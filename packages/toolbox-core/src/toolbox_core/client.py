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
from typing import Any, Callable, Optional

from aiohttp import ClientSession

from .protocol import ManifestSchema, ToolSchema
from .tool import ToolboxTool, filter_required_authn_params


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
            url: The base URL for the Toolbox service API (e.g., "http://localhost:8000").
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
        auth_token_getters: dict[str, Callable[[], str]],
    ) -> ToolboxTool:
        """Internal helper to create a callable tool from its schema."""
        # sort into authenticated and reg params
        params = []
        authn_params: dict[str, list[str]] = {}
        auth_sources: set[str] = set()
        for p in schema.parameters:
            if not p.authSources:
                params.append(p)
            else:
                authn_params[p.name] = p.authSources
                auth_sources.update(p.authSources)

        authn_params = filter_required_authn_params(authn_params, auth_sources)

        tool = ToolboxTool(
            session=self.__session,
            base_url=self.__base_url,
            name=name,
            desc=schema.description,
            params=[p.to_param() for p in params],
            required_authn_params=types.MappingProxyType(authn_params),
            auth_service_token_getters=auth_token_getters,
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
        auth_token_getters: dict[str, Callable[[], str]] = {},
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
            # TODO: Better exception
            raise Exception(f"Tool '{name}' not found!")
        tool = self.__parse_tool(name, manifest.tools[name], auth_token_getters)

        return tool

    async def load_toolset(
        self,
        name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
    ) -> list[ToolboxTool]:
        """
        Asynchronously fetches a toolset and loads all tools defined within it.

        Args:
            name: Name of the toolset to load tools.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.


        Returns:
            list[ToolboxTool]: A list of callables, one for each tool defined
            in the toolset.
        """
        # Request the definition of the tool from the server
        url = f"{self.__base_url}/api/toolset/{name}"
        async with self.__session.get(url) as response:
            json = await response.json()
        manifest: ManifestSchema = ManifestSchema(**json)

        # parse each tools name and schema into a list of ToolboxTools
        tools = [
            self.__parse_tool(n, s, auth_token_getters)
            for n, s in manifest.tools.items()
        ]
        return tools
