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

from typing import Any, Awaitable, Callable, Mapping, Optional, Union
from warnings import warn

from aiohttp import ClientSession
from toolbox_core.client import ToolboxClient as ToolboxCoreClient

from .async_tools import AsyncToolboxTool


# This class is an internal implementation detail and is not exposed to the
# end-user. It should not be used directly by external code. Changes to this
# class will not be considered breaking changes to the public API.
class AsyncToolboxClient:

    def __init__(
        self,
        url: str,
        session: ClientSession,
        client_headers: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]
        ] = None,
    ):
        """
        Initializes the AsyncToolboxClient for the Toolbox service at the given URL.

        Args:
            url: The base URL of the Toolbox service.
            session: An HTTP client session.
        """
        self.__core_client = ToolboxCoreClient(
            url=url, session=session, client_headers=client_headers
        )

    async def aload_tool(
        self,
        tool_name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        auth_tokens: Optional[dict[str, Callable[[], str]]] = None,
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
        bound_params: dict[str, Union[Any, Callable[[], Any]]] = {},
    ) -> AsyncToolboxTool:
        """
        Loads the tool with the given tool name from the Toolbox service.

        Args:
            tool_name: The name of the tool to load.
            auth_token_getters: An optional mapping of authentication source
                names to functions that retrieve ID tokens.
            auth_tokens: Deprecated. Use `auth_token_getters` instead.
            auth_headers: Deprecated. Use `auth_token_getters` instead.
            bound_params: An optional mapping of parameter names to their
                bound values.

        Returns:
            A tool loaded from the Toolbox.
        """
        if auth_tokens:
            if auth_token_getters:
                warn(
                    "Both `auth_token_getters` and `auth_tokens` are provided. `auth_tokens` is deprecated, and `auth_token_getters` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_tokens` is deprecated. Use `auth_token_getters` instead.",
                    DeprecationWarning,
                )
                auth_token_getters = auth_tokens

        if auth_headers:
            if auth_token_getters:
                warn(
                    "Both `auth_token_getters` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_token_getters` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_headers` is deprecated. Use `auth_token_getters` instead.",
                    DeprecationWarning,
                )
                auth_token_getters = auth_headers

        core_tool = await self.__core_client.load_tool(
            name=tool_name,
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
        )
        return AsyncToolboxTool(core_tool=core_tool)

    async def aload_toolset(
        self,
        toolset_name: Optional[str] = None,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        auth_tokens: Optional[dict[str, Callable[[], str]]] = None,
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
        bound_params: dict[str, Union[Any, Callable[[], Any]]] = {},
        strict: bool = False,
    ) -> list[AsyncToolboxTool]:
        """
        Loads tools from the Toolbox service, optionally filtered by toolset
        name.

        Args:
            toolset_name: The name of the toolset to load. If not provided,
                all tools are loaded.
            auth_token_getters: An optional mapping of authentication source
                names to functions that retrieve ID tokens.
            auth_tokens: Deprecated. Use `auth_token_getters` instead.
            auth_headers: Deprecated. Use `auth_token_getters` instead.
            bound_params: An optional mapping of parameter names to their
                bound values.
            strict: If True, raises an error if *any* loaded tool instance fails
                to utilize at least one provided parameter or auth token (if any
                provided). If False (default), raises an error only if a
                user-provided parameter or auth token cannot be applied to *any*
                loaded tool across the set.

        Returns:
            A list of all tools loaded from the Toolbox.
        """
        if auth_tokens:
            if auth_token_getters:
                warn(
                    "Both `auth_token_getters` and `auth_tokens` are provided. `auth_tokens` is deprecated, and `auth_token_getters` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_tokens` is deprecated. Use `auth_token_getters` instead.",
                    DeprecationWarning,
                )
                auth_token_getters = auth_tokens

        if auth_headers:
            if auth_token_getters:
                warn(
                    "Both `auth_token_getters` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_token_getters` will be used.",
                    DeprecationWarning,
                )
            else:
                warn(
                    "Argument `auth_headers` is deprecated. Use `auth_token_getters` instead.",
                    DeprecationWarning,
                )
                auth_token_getters = auth_headers

        core_tools = await self.__core_client.load_toolset(
            name=toolset_name,
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
            strict=strict,
        )

        tools = []
        for core_tool in core_tools:
            tools.append(AsyncToolboxTool(core_tool=core_tool))
        return tools

    def load_tool(
        self,
        tool_name: str,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        auth_tokens: Optional[dict[str, Callable[[], str]]] = None,
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
        bound_params: dict[str, Union[Any, Callable[[], Any]]] = {},
    ) -> AsyncToolboxTool:
        raise NotImplementedError("Synchronous methods not supported by async client.")

    def load_toolset(
        self,
        toolset_name: Optional[str] = None,
        auth_token_getters: dict[str, Callable[[], str]] = {},
        auth_tokens: Optional[dict[str, Callable[[], str]]] = None,
        auth_headers: Optional[dict[str, Callable[[], str]]] = None,
        bound_params: dict[str, Union[Any, Callable[[], Any]]] = {},
        strict: bool = False,
    ) -> list[AsyncToolboxTool]:
        raise NotImplementedError("Synchronous methods not supported by async client.")

    async def close(self):
        """Close the underlying synchronous client."""
        await self.__core_client.close()

    async def __aenter__(self):
        """
        Enter the runtime context related to this client instance.

        Allows the client to be used as an asynchronous context manager
        (e.g., `async with AsyncToolboxClient(...) as client:`).

        Returns:
            self: The client instance itself.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the runtime context and close the internally managed session.

        Allows the client to be used as an asynchronous context manager
        (e.g., `async with AsyncToolboxClient(...) as client:`).
        """
        await self.close()
