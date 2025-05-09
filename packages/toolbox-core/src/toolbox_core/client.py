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
import types
from typing import Any, Callable, Coroutine, Mapping, Optional, Union

from aiohttp import ClientSession

from .protocol import ManifestSchema, ToolSchema
from .tool import ToolboxTool
from .utils import identify_required_authn_params, resolve_value


class ToolboxClient:
    """
    An asynchronous client for interacting with a Toolbox service.

    Provides methods to discover and load tools defined by a remote Toolbox
    service endpoint. It manages an underlying `aiohttp.ClientSession`.
    """

    __base_url: str
    __session: ClientSession

    def __init__(
        self,
        url: str,
        session: Optional[ClientSession] = None,
        client_headers: Optional[Mapping[str, Union[Callable, Coroutine, str]]] = None,
    ):
        """
        Initializes the ToolboxClient.

        Args:
            url: The base URL for the Toolbox service API (e.g., "http://localhost:5000").
            session: An optional existing `aiohttp.ClientSession` to use.
                If None (default), a new session is created internally. Note that
                if a session is provided, its lifecycle (including closing)
                should typically be managed externally.
            client_headers: Headers to include in each request sent through this client.
        """
        self.__base_url = url

        # If no aiohttp.ClientSession is provided, make our own
        if session is None:
            session = ClientSession()
        self.__session = session

        self.__client_headers = client_headers if client_headers is not None else {}

    def __parse_tool(
        self,
        name: str,
        schema: ToolSchema,
        auth_token_getters: dict[str, Callable[[], str]],
        all_bound_params: Mapping[str, Union[Callable[[], Any], Any]],
        client_headers: Mapping[str, Union[Callable, Coroutine, str]],
    ) -> tuple[ToolboxTool, set[str], set[str]]:
        """Internal helper to create a callable tool from its schema."""
        # sort into reg, authn, and bound params
        params = []
        authn_params: dict[str, list[str]] = {}
        bound_params: dict[str, Callable[[], str]] = {}
        for p in schema.parameters:
            if p.authSources:  # authn parameter
                authn_params[p.name] = p.authSources
            elif p.name in all_bound_params:  # bound parameter
                bound_params[p.name] = all_bound_params[p.name]
            else:  # regular parameter
                params.append(p)

        authn_params = identify_required_authn_params(
            authn_params, auth_token_getters.keys()
        )

        tool = ToolboxTool(
            session=self.__session,
            base_url=self.__base_url,
            name=name,
            description=schema.description,
            params=params,
            # create a read-only values for the maps to prevent mutation
            required_authn_params=types.MappingProxyType(authn_params),
            auth_service_token_getters=types.MappingProxyType(auth_token_getters),
            bound_params=types.MappingProxyType(bound_params),
            client_headers=types.MappingProxyType(client_headers),
        )

        used_bound_keys = set(bound_params.keys())
        used_auth_keys: set[str] = set()
        for required_sources in authn_params.values():
            used_auth_keys.update(required_sources)

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
        is responsible for its lifecycle, but calling close here will still
        attempt to close it.
        """
        await self.__session.close()

    async def load_tool(
        self,
        name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
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

        """
        # Resolve client headers
        resolved_headers = {
            name: await resolve_value(val)
            for name, val in self.__client_headers.items()
        }

        # request the definition of the tool from the server
        url = f"{self.__base_url}/api/tool/{name}"
        async with self.__session.get(url, headers=resolved_headers) as response:
            json = await response.json()
        manifest: ManifestSchema = ManifestSchema(**json)

        # parse the provided definition to a tool
        if name not in manifest.tools:
            # TODO: Better exception
            raise Exception(f"Tool '{name}' not found!")
        tool, _, _ = self.__parse_tool(
            name,
            manifest.tools[name],
            auth_token_getters,
            bound_params,
            self.__client_headers,
        )

        return tool

    async def load_toolset(
        self,
        name: Optional[str] = None,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
    ) -> list[ToolboxTool]:
        """
        Asynchronously fetches a toolset and loads all tools defined within it.

        Args:
            name: Name of the toolset to load tools.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.

        Returns:
            list[ToolboxTool]: A list of callables, one for each tool defined
            in the toolset.
        """
        # Resolve client headers
        original_headers = self.__client_headers
        resolved_headers = {
            header_name: await resolve_value(original_headers[header_name])
            for header_name in original_headers
        }
        # Request the definition of the tool from the server
        url = f"{self.__base_url}/api/toolset/{name or ''}"
        async with self.__session.get(url, headers=resolved_headers) as response:
            json = await response.json()
        manifest: ManifestSchema = ManifestSchema(**json)

        # parse each tools name and schema into a list of ToolboxTools
        tools = [
            self.__parse_tool(
                n, s, auth_token_getters, bound_params, self.__client_headers
            )[0]
            for n, s in manifest.tools.items()
        ]
        return tools

    async def add_headers(
        self, headers: Mapping[str, Union[Callable, Coroutine, str]]
    ) -> None:
        """
        Asynchronously Add headers to be included in each request sent through this client.

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
