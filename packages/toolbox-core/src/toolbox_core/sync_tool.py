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
    A callable proxy object representing a specific tool on a remote Toolbox server.

    Instances of this class behave like synchronous functions. When called, they
    send a request to the corresponding tool's endpoint on the Toolbox server with
    the provided arguments.

    It utilizes Python's introspection features (`__name__`, `__doc__`,
    `__signature__`, `__annotations__`) so that standard tools like `help()`
    and `inspect` work as expected.
    """

    def __init__(
        self, async_tool: ToolboxTool, loop: AbstractEventLoop, thread: Thread
    ):
        """
        Initializes a callable that will trigger the tool invocation through the
        Toolbox server.

        Args:
            async_tool: An instance of the asynchronous ToolboxTool.
            loop: The event loop used to run asynchronous tasks.
            thread: The thread to run blocking operations in.
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

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Synchronously calls the remote tool with the provided arguments.

        Validates arguments against the tool's signature, then sends them
        as a JSON payload in a POST request to the tool's invoke URL.

        Args:
            *args: Positional arguments for the tool.
            **kwargs: Keyword arguments for the tool.

        Returns:
            The string result returned by the remote tool execution.
        """
        coro = self.__async_tool(*args, **kwargs)
        return asyncio.run_coroutine_threadsafe(coro, self.__loop).result()

    def add_auth_token_getters(
        self,
        auth_token_getters: Mapping[str, Callable[[], str]],
    ) -> "ToolboxSyncTool":
        """
        Registers an auth token getter function that is used for AuthServices when tools
        are invoked.

        Args:
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.

        Returns:
            A new ToolboxSyncTool instance with the specified authentication token
            getters registered.
        """

        new_async_tool = self.__async_tool.add_auth_token_getters(auth_token_getters)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)

    def bind_parameters(
        self, bound_params: Mapping[str, Union[Callable[[], Any], Any]]
    ) -> "ToolboxSyncTool":
        """
        Binds parameters to values or callables that produce values.

         Args:
             bound_params: A mapping of parameter names to values or callables that
                 produce values.

         Returns:
             A new ToolboxSyncTool instance with the specified parameters bound.
        """

        new_async_tool = self.__async_tool.bind_parameters(bound_params)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)
