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


from asyncio import AbstractEventLoop, new_event_loop, run_coroutine_threadsafe
from threading import Thread
from typing import Any, Awaitable, Callable, Mapping, Optional, Union

from deprecated import deprecated

from .client import ToolboxClient
from .sync_tool import ToolboxSyncTool


class ToolboxSyncClient:
    """
    A synchronous client for interacting with a Toolbox service.

    Provides methods to discover and load tools defined by a remote Toolbox
    service endpoint.
    """

    __loop: Optional[AbstractEventLoop] = None
    __thread: Optional[Thread] = None

    def __init__(
        self,
        url: str,
        client_headers: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]
        ] = None,
    ):
        """
        Initializes the ToolboxSyncClient.

        Args:
            url: The base URL for the Toolbox service API (e.g., "http://localhost:5000").
            client_headers: Headers to include in each request sent through this client.
        """
        # Running a loop in a background thread allows us to support async
        # methods from non-async environments.
        if self.__class__.__loop is None:
            loop = new_event_loop()
            thread = Thread(target=loop.run_forever, daemon=True)
            thread.start()
            self.__class__.__thread = thread
            self.__class__.__loop = loop

        async def create_client():
            return ToolboxClient(url, client_headers=client_headers)

        self.__async_client = run_coroutine_threadsafe(
            create_client(), self.__class__.__loop
        ).result()

    def close(self):
        """
        Synchronously closes the underlying client session. Doing so will cause
        any tools created by this Client to cease to function.
        """
        coro = self.__async_client.close()
        run_coroutine_threadsafe(coro, self.__loop).result()

    def load_tool(
        self,
        name: str,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ] = {},
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ] = {},
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

        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")

        async_tool = run_coroutine_threadsafe(coro, self.__loop).result()
        return ToolboxSyncTool(async_tool, self.__loop, self.__thread)

    def load_toolset(
        self,
        name: Optional[str] = None,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ] = {},
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ] = {},
        strict: bool = False,
    ) -> list[ToolboxSyncTool]:
        """
        Synchronously fetches a toolset and loads all tools defined within it.

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
            list[ToolboxSyncTool]: A list of callables, one for each tool defined
            in the toolset.

        Raises:
            ValueError: If validation fails based on the `strict` flag.
        """
        coro = self.__async_client.load_toolset(
            name, auth_token_getters, bound_params, strict
        )

        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")

        async_tools = run_coroutine_threadsafe(coro, self.__loop).result()
        return [
            ToolboxSyncTool(async_tool, self.__loop, self.__thread)
            for async_tool in async_tools
        ]

    @deprecated(
        "Use the `client_headers` parameter in the ToolboxClient constructor instead."
    )
    def add_headers(
        self,
        headers: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]
        ],
    ) -> None:
        """
        Add headers to be included in each request sent through this client.

        Args:
            headers: Headers to include in each request sent through this client.

        Raises:
            ValueError: If any of the headers are already registered in the client.
        """
        self.__async_client.add_headers(headers)

    def __enter__(self):
        """
        Enter the runtime context related to this client instance.

        Allows the client to be used as a context manager
        (e.g., `with ToolboxSyncClient(...) as client:`).

        Returns:
            self: The client instance itself.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the runtime context and close the internally managed session.

        Allows the client to be used as a context manager
        (e.g., `with ToolboxSyncClient(...) as client:`).
        """
        self.close()
