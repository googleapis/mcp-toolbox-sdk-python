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
from asyncio import AbstractEventLoop
from concurrent.futures import Future
from threading import Thread
from typing import Any, Callable, Coroutine, Mapping, Optional, Union

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
        client_headers: Optional[Mapping[str, Union[Callable, Coroutine, str]]] = None,
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
            loop = asyncio.new_event_loop()
            thread = Thread(target=loop.run_forever, daemon=True)
            thread.start()
            self.__class__.__thread = thread
            self.__class__.__loop = loop

        async def create_client():
            return ToolboxClient(url, client_headers=client_headers)

        self.__async_client = asyncio.run_coroutine_threadsafe(
            create_client(), self.__class__.__loop
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

    def _load_tool_coro(
        self,
        name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
    ) -> Coroutine[Any, Any, ToolboxSyncTool]:
        """
        Asynchronously initiates the loading of a specific tool from the Toolbox service.

        This method schedules the tool loading operation on a background event loop
        and immediately returns a `concurrent.futures.Future`. This allows other
        operations to proceed while the tool is being loaded. To get the actual
        `ToolboxSyncTool` instance, call `.result()` on the returned future, which
        will block until the tool is available or an error occurs.

        Args:
            name: The unique name or identifier of the tool to load.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.

        Returns:
            A `concurrent.futures.Future` that, upon successful completion, will
            yield a `ToolboxSyncTool` instance representing the loaded tool.

        Raises:
            ValueError: If the background event loop or thread (required for asynchronous
                        operations) is not running or properly initialized.

        """

        async def async_worker() -> ToolboxSyncTool:
            if not self.__loop or not self.__thread:
                raise ValueError("Background loop or thread cannot be None.")
            async_tool = await self.__async_client.load_tool(
                name, auth_token_getters, bound_params
            )
            return ToolboxSyncTool(async_tool, self.__loop, self.__thread)

        return async_worker()

    def _load_toolset_coro(
        self,
        name: Optional[str] = None,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
        strict: bool = False,
    ) -> Coroutine[Any, Any, list[ToolboxSyncTool]]:
        """
        Asynchronously initiates loading of all tools within a specified toolset.

        This method schedules the toolset loading operation on a background event
        loop and returns a `concurrent.futures.Future` without blocking.
        The future's result will be a list of `ToolboxSyncTool` instances.
        Call `.result()` on the returned future to wait for completion and get
        the list of tools.

        Args:
            name: Name of the toolset to load tools.
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            strict: If True, raises an error if *any* loaded tool instance fails
                to utilize at least one provided parameter or auth token (if any
                provided). If False (default), raises an error only if a
                user-provided parameter or auth token cannot be applied to *any*
                loaded tool across the set.

        Returns:
            A `concurrent.futures.Future` that, upon successful completion, will
            yield a list of `ToolboxSyncTool` instances.

        Raises:
            ValueError: If the background event loop or thread is not running,
                        or if validation fails based on the `strict` flag during
                        the underlying asynchronous loading process.
        """

        async def async_worker() -> list[ToolboxSyncTool]:
            if not self.__loop or not self.__thread:
                raise ValueError("Background loop or thread cannot be None.")
            async_tools = await self.__async_client.load_toolset(
                name, auth_token_getters, bound_params, strict
            )
            return [
                ToolboxSyncTool(async_tool, self.__loop, self.__thread)
                for async_tool in async_tools
            ]

        return async_worker()

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
        coro = self._load_tool_coro(name, auth_token_getters, bound_params)
        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")
        future = asyncio.run_coroutine_threadsafe(coro, self.__loop)
        return future.result()

    def load_toolset(
        self,
        name: Optional[str] = None,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {},
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
                to utilize at least one provided parameter or auth token (if any
                provided). If False (default), raises an error only if a
                user-provided parameter or auth token cannot be applied to *any*
                loaded tool across the set.

        Returns:
            list[ToolboxSyncTool]: A list of callables, one for each tool defined
            in the toolset.

        Raises:
            ValueError: If validation fails based on the `strict` flag.
        """
        coro = self._load_toolset_coro(
            name, auth_token_getters, bound_params, strict
        )
        if not self.__loop or not self.__thread:
            raise ValueError("Background loop or thread cannot be None.")
        future = asyncio.run_coroutine_threadsafe(coro, self.__loop)
        return future.result()

    def add_headers(
        self, headers: Mapping[str, Union[Callable, Coroutine, str]]
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
        """Enter the runtime context related to this client instance."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and close the client session."""
        self.close()
