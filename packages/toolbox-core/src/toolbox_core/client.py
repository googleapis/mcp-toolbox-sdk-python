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


from typing import Any, Callable, Mapping, Optional, Sequence, Union

from aiohttp import ClientSession

from .protocol import ManifestSchema, ParameterSchema, ToolSchema
from .tool import ToolboxTool


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
    ):
        """
        Initializes the ToolboxClient.

        Args:
            url: The base URL for the Toolbox service API (e.g., "http://localhost:5000").
            session: An optional existing `aiohttp.ClientSession` to use.
                If None (default), a new session is created internally. Note that
                if a session is provided, its lifecycle (including closing)
                should typically be managed externally.
        """
        self.__base_url = url

        # If no aiohttp.ClientSession is provided, make our own
        if session is None:
            session = ClientSession()
        self.__session = session

    def __parse_tool(
        self,
        name: str,
        schema: ToolSchema,
        auth_token_getters: Mapping[str, Callable[[], str]],
        all_bound_params: Mapping[str, Union[Callable[[], Any], Any]],
        strict: bool,
    ) -> ToolboxTool:
        """
        Internal helper to create a callable ToolboxTool from its schema.

        Args:
            name: The name of the tool.
            schema: The ToolSchema defining the tool.
            auth_token_getters: Mapping of auth service names to token getters.
            all_bound_params: Mapping of all initially bound parameter names to values/callables.
            strict: The strictness setting for the created ToolboxTool instance.

        Returns:
            An initialized ToolboxTool instance.
        """

        params: Sequence[ParameterSchema] = (
            schema.parameters if schema.parameters is not None else []
        )

        tool = ToolboxTool(
            session=self.__session,
            base_url=self.__base_url,
            name=name,
            description=schema.description,
            params=params,
            auth_service_token_getters=auth_token_getters,
            bound_params=all_bound_params,
            strict=strict,
        )
        return tool

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
        auth_token_getters: Mapping[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
        strict: bool = True,
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
            strict: If True (default), the loaded tool instance will operate in
                    strict validation mode. If False, it will be non-strict.

        Returns:
            ToolboxTool: A callable object representing the loaded tool, ready
                for execution. The specific arguments and behavior of the callable
                depend on the tool itself.

        """

        # request the definition of the tool from the server
        url = f"{self.__base_url}/api/tool/{name}"
        async with self.__session.get(url) as response:
            json = await response.json()
        manifest: ManifestSchema = ManifestSchema(**json)

        # parse the provided definition to a tool
        if name not in manifest.tools:
            raise Exception(
                f"Tool '{name}' not found in the manifest received from {url}"
            )
        tool = self.__parse_tool(
            name, manifest.tools[name], auth_token_getters, bound_params, strict
        )

        return tool

    async def load_toolset(
        self,
        name: Optional[str] = None,
        auth_token_getters: Mapping[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
        strict: bool = True,
    ) -> list[ToolboxTool]:
        """
        Asynchronously fetches a toolset and loads all tools defined within it.

        Args:
            name: Optional name of the toolset to load. If None, attempts to load
                the default toolset.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            strict: If True (default), all loaded tool instances will operate in
                    strict validation mode. If False, they will be non-strict.

        Returns:
            list[ToolboxTool]: A list of callables, one for each tool defined in
            the toolset.
        """
        # Request the definition of the tool from the server
        url = f"{self.__base_url}/api/toolset/{name or ''}"
        async with self.__session.get(url) as response:
            json = await response.json()
        manifest: ManifestSchema = ManifestSchema(**json)

        # parse each tools name and schema into a list of ToolboxTools
        tools = [
            self.__parse_tool(n, s, auth_token_getters, bound_params, strict)
            for n, s in manifest.tools.items()
        ]
        return tools
