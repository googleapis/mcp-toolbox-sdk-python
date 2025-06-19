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
from inspect import Signature
from threading import Thread
from typing import Any, Awaitable, Callable, Mapping, Sequence, Union

from .protocol import ParameterSchema
from .tool import ToolboxTool


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

        # NOTE: We cannot define __qualname__ as a @property here.
        # Properties are designed to compute values dynamically when accessed on an *instance* (using 'self').
        # However, Python needs the class's __qualname__ attribute to be a plain string
        # *before* any instances exist, specifically when the 'class ToolboxSyncTool:' statement
        # itself is being processed during module import or class definition.
        # Defining __qualname__ as a property leads to a TypeError because the class object needs
        # a string value immediately, not a descriptor that evaluates later.
        self.__qualname__ = (
            f"{self.__class__.__qualname__}.{self.__async_tool.__name__}"
        )

    @property
    def __name__(self) -> str:
        return self.__async_tool.__name__

    @property
    def __doc__(self) -> Union[str, None]:  # type: ignore[override]
        # Standard Python object attributes like __doc__ are technically "writable".
        # But not defining a setter function makes this a read-only property.
        # Mypy flags this issue in the type checks.
        return self.__async_tool.__doc__

    @property
    def __signature__(self) -> Signature:
        return self.__async_tool.__signature__

    @property
    def __annotations__(self) -> dict[str, Any]:  # type: ignore[override]
        # Standard Python object attributes like __doc__ are technically "writable".
        # But not defining a setter function makes this a read-only property.
        # Mypy flags this issue in the type checks.
        return self.__async_tool.__annotations__

    @property
    def _name(self) -> str:
        return self.__async_tool._name

    @property
    def _description(self) -> str:
        return self.__async_tool._description

    @property
    def _params(self) -> Sequence[ParameterSchema]:
        return self.__async_tool._params

    @property
    def _bound_params(
        self,
    ) -> Mapping[str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]]:
        return self.__async_tool._bound_params

    @property
    def _required_authn_params(self) -> Mapping[str, list[str]]:
        return self.__async_tool._required_authn_params

    @property
    def _required_authz_tokens(self) -> Sequence[str]:
        return self.__async_tool._required_authz_tokens

    @property
    def _auth_service_token_getters(
        self,
    ) -> Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]]]]:
        return self.__async_tool._auth_service_token_getters

    @property
    def _client_headers(
        self,
    ) -> Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]:
        return self.__async_tool._client_headers

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
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ],
    ) -> "ToolboxSyncTool":
        """
        Registers auth token getter functions that are used for AuthServices
        when tools are invoked.

        Args:
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.

        Returns:
            A new ToolboxSyncTool instance with the specified authentication
            token getters registered.

        Raises:
            ValueError: If an auth source has already been registered either to
                the tool or to the corresponding client.

        """
        new_async_tool = self.__async_tool.add_auth_token_getters(auth_token_getters)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)

    def add_auth_token_getter(
        self,
        auth_source: str,
        get_id_token: Union[Callable[[], str], Callable[[], Awaitable[str]]],
    ) -> "ToolboxSyncTool":
        """
        Registers an auth token getter function that is used for AuthService
        when tools are invoked.

        Args:
            auth_source: The name of the authentication source.
            get_id_token: A function that returns the ID token.

        Returns:
            A new ToolboxSyncTool instance with the specified authentication
            token getter registered.

        Raises:
            ValueError: If the auth source has already been registered either to
                the tool or to the corresponding client.

        """
        return self.add_auth_token_getters({auth_source: get_id_token})

    def bind_params(
        self,
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ],
    ) -> "ToolboxSyncTool":
        """
        Binds parameters to values or callables that produce values.

        Args:
            bound_params: A mapping of parameter names to values or callables
                that produce values.

        Returns:
            A new ToolboxSyncTool instance with the specified parameters bound.

        Raises:
            ValueError: If a parameter is already bound or is not defined by the
                tool's definition.

        """
        new_async_tool = self.__async_tool.bind_params(bound_params)
        return ToolboxSyncTool(new_async_tool, self.__loop, self.__thread)

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any],
    ) -> "ToolboxSyncTool":
        """
        Binds a parameter to the value or callable that produce the value.

        Args:
            param_name: The name of the bound parameter.
            param_value: The value of the bound parameter, or a callable that
                returns the value.

        Returns:
            A new ToolboxSyncTool instance with the specified parameter bound.

        Raises:
            ValueError: If the parameter is already bound or is not defined by
                the tool's definition.

        """
        return self.bind_params({param_name: param_value})
