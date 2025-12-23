# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from types import MappingProxyType
from typing import Any, Awaitable, Callable, Mapping, Optional, Union

from aiohttp import ClientSession
from deprecated import deprecated

from .itransport import ITransport
from .mcp_transport import (
    McpHttpTransportV20241105,
    McpHttpTransportV20250326,
    McpHttpTransportV20250618,
)
from .protocol import Protocol, ToolSchema
from .tool import ToolboxTool
from .toolbox_transport import ToolboxTransport
from .utils import identify_auth_requirements, resolve_value


class ToolboxClient:
    """
    An asynchronous client for interacting with a Toolbox service.

    Provides methods to discover and load tools defined by a remote Toolbox
    service endpoint. It manages an underlying `aiohttp.ClientSession`, if one
    is not provided.
    """

    __transport: ITransport

    def __init__(
        self,
        url: str,
        session: Optional[ClientSession] = None,
        client_headers: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]
        ] = None,
        protocol: Protocol = Protocol.MCP,
    ):
        """
        Initializes the ToolboxClient.

        Args:
            url: The base URL for the Toolbox service API (e.g., "http://localhost:5000").
            session: An optional existing `aiohttp.ClientSession` to use.
                If None (default), a new session is created internally. Note that
                if a session is provided, its lifecycle (including closing)
                should typically be managed externally.
            client_headers: Headers to include in each request sent through this
            client.
            protocol: The communication protocol to use.
        """
        if protocol == Protocol.TOOLBOX:
            self.__transport = ToolboxTransport(url, session)
        elif protocol in Protocol.get_supported_mcp_versions():
            if protocol == Protocol.MCP_v20250618:
                self.__transport = McpHttpTransportV20250618(url, session, protocol)
            elif protocol == Protocol.MCP_v20250326:
                self.__transport = McpHttpTransportV20250326(url, session, protocol)
            elif protocol == Protocol.MCP_v20241105:
                self.__transport = McpHttpTransportV20241105(url, session, protocol)
        else:
            raise ValueError(f"Unsupported MCP protocol version: {protocol}")

        self.__client_headers = client_headers if client_headers is not None else {}

    def __parse_tool(
        self,
        name: str,
        schema: ToolSchema,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ],
        all_bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ],
        client_headers: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]
        ],
    ) -> tuple[ToolboxTool, set[str], set[str]]:
        """Internal helper to create a callable tool from its schema."""
        # sort into reg, authn, and bound params
        params = []
        authn_params: dict[str, list[str]] = {}
        bound_params: dict[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ] = {}
        for p in schema.parameters:
            if p.authSources:  # authn parameter
                authn_params[p.name] = p.authSources
            elif p.name in all_bound_params:  # bound parameter
                bound_params[p.name] = all_bound_params[p.name]
            else:  # regular parameter
                params.append(p)

        authn_params, authz_tokens, used_auth_keys = identify_auth_requirements(
            authn_params,
            schema.authRequired,
            auth_token_getters.keys(),
        )

        tool = ToolboxTool(
            transport=self.__transport,
            name=name,
            description=schema.description,
            # create a read-only values to prevent mutation
            params=tuple(params),
            required_authn_params=MappingProxyType(authn_params),
            required_authz_tokens=authz_tokens,
            auth_service_token_getters=MappingProxyType(auth_token_getters),
            bound_params=MappingProxyType(bound_params),
            client_headers=MappingProxyType(client_headers),
        )

        used_bound_keys = set(bound_params.keys())

        return tool, used_auth_keys, used_bound_keys

    async def __aenter__(self):
        """
        Enter the runtime context related to this client instance.

        Allows the client to be used as an asynchronous context manager
        (e.g., `async with ToolboxClient(...) as client:`).

        Returns:
            self: The client instance itself.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the runtime context and close the internally managed session.

        Allows the client to be used as an asynchronous context manager
        (e.g., `async with ToolboxClient(...) as client:`).
        """
        await self.close()

    async def close(self):
        """
        Asynchronously closes the underlying client session. Doing so will cause
        any tools created by this Client to cease to function.

        If the session was provided externally during initialization, the caller
        is responsible for its lifecycle.
        """
        await self.__transport.close()

    async def load_tool(
        self,
        name: str,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ] = {},
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ] = {},
    ) -> ToolboxTool:
        """
        Asynchronously loads a tool from the server.

        Retrieves the schema for the specified tool from the Toolbox server and
        returns a callable object (`ToolboxTool`) that can be used to invoke the
        tool remotely.

        Args:
            name: The unique name or identifier of the tool to load.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.

        Returns:
            ToolboxTool: A callable object representing the loaded tool, ready
                for execution. The specific arguments and behavior of the callable
                depend on the tool itself.

        Raises:
            ValueError: If the loaded tool instance fails to utilize at least
                one provided parameter or auth token (if any provided).
        """
        # Resolve client headers
        resolved_headers = {
            name: await resolve_value(val)
            for name, val in self.__client_headers.items()
        }

        manifest = await self.__transport.tool_get(name, resolved_headers)

        # parse the provided definition to a tool
        if name not in manifest.tools:
            # TODO: Better exception
            raise ValueError(f"Tool '{name}' not found!")
        tool, used_auth_keys, used_bound_keys = self.__parse_tool(
            name,
            manifest.tools[name],
            auth_token_getters,
            bound_params,
            self.__client_headers,
        )

        provided_auth_keys = set(auth_token_getters.keys())
        provided_bound_keys = set(bound_params.keys())

        unused_auth = provided_auth_keys - used_auth_keys
        unused_bound = provided_bound_keys - used_bound_keys

        if unused_auth or unused_bound:
            error_messages = []
            if unused_auth:
                error_messages.append(f"unused auth tokens: {', '.join(unused_auth)}")
            if unused_bound:
                error_messages.append(
                    f"unused bound parameters: {', '.join(unused_bound)}"
                )
            raise ValueError(
                f"Validation failed for tool '{name}': { '; '.join(error_messages) }."
            )

        return tool

    async def load_toolset(
        self,
        name: Optional[str] = None,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ] = {},
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ] = {},
        strict: bool = False,
    ) -> list[ToolboxTool]:
        """
        Asynchronously fetches a toolset and loads all tools defined within it.

        Args:
            name: Name of the toolset to load. If None, loads the default toolset.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            strict: If True, raises an error if *any* loaded tool instance fails
                to utilize all of the given parameters or auth tokens. (if any
                provided). If False (default), raises an error only if a
                user-provided parameter or auth token cannot be applied to *any*
                loaded tool across the set.

        Returns:
            list[ToolboxTool]: A list of callables, one for each tool defined
            in the toolset.

        Raises:
            ValueError: If validation fails based on the `strict` flag.
        """

        # Resolve client headers
        original_headers = self.__client_headers
        resolved_headers = {
            header_name: await resolve_value(original_headers[header_name])
            for header_name in original_headers
        }

        manifest = await self.__transport.tools_list(name, resolved_headers)

        tools: list[ToolboxTool] = []
        overall_used_auth_keys: set[str] = set()
        overall_used_bound_params: set[str] = set()
        provided_auth_keys = set(auth_token_getters.keys())
        provided_bound_keys = set(bound_params.keys())

        # parse each tool's name and schema into a list of ToolboxTools
        for tool_name, schema in manifest.tools.items():
            tool, used_auth_keys, used_bound_keys = self.__parse_tool(
                tool_name,
                schema,
                auth_token_getters,
                bound_params,
                self.__client_headers,
            )
            tools.append(tool)

            if strict:
                unused_auth = provided_auth_keys - used_auth_keys
                unused_bound = provided_bound_keys - used_bound_keys
                if unused_auth or unused_bound:
                    error_messages = []
                    if unused_auth:
                        error_messages.append(
                            f"unused auth tokens: {', '.join(unused_auth)}"
                        )
                    if unused_bound:
                        error_messages.append(
                            f"unused bound parameters: {', '.join(unused_bound)}"
                        )
                    raise ValueError(
                        f"Validation failed for tool '{tool_name}': { '; '.join(error_messages) }."
                    )
            else:
                overall_used_auth_keys.update(used_auth_keys)
                overall_used_bound_params.update(used_bound_keys)

        unused_auth = provided_auth_keys - overall_used_auth_keys
        unused_bound = provided_bound_keys - overall_used_bound_params

        if unused_auth or unused_bound:
            error_messages = []
            if unused_auth:
                error_messages.append(
                    f"unused auth tokens could not be applied to any tool: {', '.join(unused_auth)}"
                )
            if unused_bound:
                error_messages.append(
                    f"unused bound parameters could not be applied to any tool: {', '.join(unused_bound)}"
                )
            raise ValueError(
                f"Validation failed for toolset '{name or 'default'}': { '; '.join(error_messages) }."
            )

        return tools

    @deprecated(
        "Use the `client_headers` parameter in the ToolboxClient constructor instead."
    )
    def add_headers(
        self,
        headers: Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]]]],
    ) -> None:
        """
        Add headers to be included in each request sent through this client.
        Args:
            headers: Headers to include in each request sent through this client.
        Raises:
            ValueError: If any of the headers are already registered in the client.
        """
        existing_headers = self.__client_headers.keys()
        incoming_headers = headers.keys()
        duplicates = existing_headers & incoming_headers
        if duplicates:
            raise ValueError(
                f"Client header(s) `{', '.join(duplicates)}` already registered in the client."
            )

        merged_headers = {**self.__client_headers, **headers}
        self.__client_headers = merged_headers
