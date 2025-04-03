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
from threading import Thread
from typing import Any, Awaitable, Callable, Mapping, TypeVar, Union

from .tool import ToolboxTool

T = TypeVar("T")


class ToolboxSyncTool:
    """
    A synchronous wrapper proxying asynchronous ToolboxTool instance.

    This class allows calling the underlying async tool synchronously.
    It also proxies methods like `add_auth_token_getters` and
    `bind_parameters` to ensure they return new instances of this synchronous
    wrapper.
    """

    def __init__(
        self, async_tool: ToolboxTool, loop: AbstractEventLoop, thread: Thread
    ):
        """
        Initializes the synchronous wrapper.

        Args:
            async_tool: An instance of the asynchronous ToolboxTool.
        """

        if not isinstance(async_tool, ToolboxTool):
            raise TypeError("async_tool must be an instance of ToolboxTool")

        self.__async_tool = async_tool
        self.__loop = loop
        self.__thread = thread

        # Delegate introspection attributes to the wrapped async tool
        self.__name__ = self.__async_tool.__name__
        self.__doc__ = self.__async_tool.__doc__
        self.__signature__ = self.__async_tool.__signature__
        self.__annotations__ = self.__async_tool.__annotations__
        # TODO: self.__qualname__ ?? (Consider if needed)

    def __run_as_sync(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine synchronously"""
        if not self.__loop:
            raise Exception(
                "Cannot call synchronous methods before the background loop is initialized."
            )
        return asyncio.run_coroutine_threadsafe(coro, self.__loop).result()

    async def __run_as_async(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine asynchronously"""

        # If a loop has not been provided, attempt to run in current thread.
        if not self.__loop:
            return await coro

        # Otherwise, run in the background thread.
        return await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro, self.__loop)
        )

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Synchronously calls the underlying remote tool.

        This method blocks until the tool call completes and returns
        the result.

        Args:
            *args: Positional arguments for the tool.
            **kwargs: Keyword arguments for the tool.

        Returns:
            The string result returned by the remote tool execution.

        Raises:
            Any exception raised by the underlying async tool's __call__ method
            or during asyncio execution.
        """
        return self.__run_as_sync(self.__async_tool(**kwargs))

    def add_auth_token_getters(
        self,
        auth_token_getters: Mapping[str, Callable[[], str]],
    ) -> "ToolboxSyncTool":
        """
        Registers auth token getters and returns a new SyncToolboxTool instance.

        Args:
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.

        Returns:
            A new SyncToolboxTool instance wrapping the updated async tool.
        """

        new_async_tool = self.__async_tool.add_auth_token_getters(auth_token_getters)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)

    def bind_parameters(
        self, bound_params: Mapping[str, Union[Callable[[], Any], Any]]
    ) -> "ToolboxSyncTool":
        """
        Binds parameters and returns a new SyncToolboxTool instance.

         Args:
             bound_params: A mapping of parameter names to values or callables that
                 produce values.

         Returns:
             A new SyncToolboxTool instance wrapping the updated async tool.
        """

        new_async_tool = self.__async_tool.bind_parameters(bound_params)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)
