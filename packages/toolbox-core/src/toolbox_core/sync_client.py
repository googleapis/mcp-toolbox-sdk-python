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

import asyncio
from threading import Thread
from typing import Any, Awaitable, Callable, Mapping, Optional, TypeVar, Union

from aiohttp import ClientSession

from .client import ToolboxClient
from .sync_tool import ToolboxSyncTool

T = TypeVar("T")


class ToolboxSyncClient:
    """
    An synchronous client for interacting with a Toolbox service.

    Provides methods to discover and load tools defined by a remote Toolbox
    service endpoint.
    """

    __loop: Optional[asyncio.AbstractEventLoop] = None
    __thread: Optional[Thread] = None

    def __init__(
        self,
        url: str,
    ):
        """
        Initializes the ToolboxSyncClient.

        Args:
            url: The base URL for the Toolbox service API (e.g., "http://localhost:5000").
        """
        # Running a loop in a background thread allows us to support async
        # methods from non-async environments.
        if self.__class__.__loop is None:
            loop = asyncio.new_event_loop()
            thread = Thread(target=loop.run_forever, daemon=True)
            thread.start()
            self.__class__.__thread = thread
            self.__class__.__loop = loop

        async def create_client():
            return ToolboxClient(url)

        # Ignoring type since we're already checking the existence of a loop above.
        self.__async_client = asyncio.run_coroutine_threadsafe(
            create_client(), self.__class__.__loop  # type: ignore
        ).result()

    def close(self):
        """
        Synchronously closes the underlying client session. Doing so will cause
        any tools created by this Client to cease to function.

        If the session was provided externally during initialization, the caller
        is responsible for its lifecycle, but calling close here will still
        attempt to close it.
        """
        coro = self.__async_client.close()
        asyncio.run_coroutine_threadsafe(coro, self.__loop).result()

    def load_tool(
        self,
        name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
    ) -> ToolboxSyncTool:
        """
        Synchronously loads a tool from the server.

        Retrieves the schema for the specified tool from the Toolbox server and
        returns a callable object (`ToolboxSyncTool`) that can be used to invoke the
        tool remotely.

        Args:
            name: The unique name or identifier of the tool to load.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.

        Returns:
            ToolboxSyncTool: A callable object representing the loaded tool, ready
                for execution. The specific arguments and behavior of the callable
                depend on the tool itself.
        """
        coro = self.__async_client.load_tool(name, auth_token_getters, bound_params)

        # We have already created a new loop in the init method in case it does not already exist
        async_tool = asyncio.run_coroutine_threadsafe(coro, self.__loop).result()  # type: ignore

        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")
        return ToolboxSyncTool(async_tool, self.__loop, self.__thread)

    def load_toolset(
        self,
        name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
    ) -> list[ToolboxSyncTool]:
        """
        Synchronously fetches a toolset and loads all tools defined within it.

        Args:
            name: Name of the toolset to load tools.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.

        Returns:
            list[ToolboxSyncTool]: A list of callables, one for each tool defined
            in the toolset.
        """
        coro = self.__async_client.load_toolset(name, auth_token_getters, bound_params)

        # We have already created a new loop in the init method in case it does not already exist
        async_tools = asyncio.run_coroutine_threadsafe(coro, self.__loop).result()  # type: ignore

        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")
        return [
            ToolboxSyncTool(async_tool, self.__loop, self.__thread)
            for async_tool in async_tools
        ]

    def __enter__(self):
        """Enter the runtime context related to this client instance."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and close the client session."""
        self.close()
