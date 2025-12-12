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

from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Union

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from typing_extensions import override

from .client import ToolboxClient
from .credentials import CredentialConfig
from .tool import ToolboxContext, ToolboxTool


class ToolboxToolset(BaseToolset):
    """
    A Toolset that provides tools from a remote Toolbox server.
    """

    def __init__(
        self,
        server_url: str,
        toolset_name: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        credentials: Optional[CredentialConfig] = None,
        additional_headers: Optional[
            Dict[str, Union[str, Callable[[], str], Callable[[], Awaitable[str]]]]
        ] = None,
        bound_params: Optional[Mapping[str, Union[Callable[[], Any], Any]]] = None,
        auth_token_getters: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]]]]
        ] = None,
        pre_hook: Optional[Callable[[ToolboxContext], Awaitable[None]]] = None,
        post_hook: Optional[Callable[[ToolboxContext], Awaitable[None]]] = None,
        **kwargs: Any,
    ):
        """
        Args:
            server_url: The URL of the Toolbox server.
            toolset_name: The name of the remote toolset to load.
            tool_names: Specific tool names to load (alternative to toolset_name).
            credentials: Authentication configuration.
            additional_headers: Extra headers (static or dynamic).
            bound_params: Parameters to bind globally to loaded tools.
            auth_token_getters: Mapping of auth service names to token getters.
            pre_hook: Hook to run before every tool execution.
            post_hook: Hook to run after every tool execution.
        """
        super().__init__()
        self._client = ToolboxClient(
            server_url=server_url,
            credentials=credentials,
            additional_headers=additional_headers,
            **kwargs,
        )
        self._toolset_name = toolset_name
        self._tool_names = tool_names
        self._bound_params = bound_params
        self._auth_token_getters = auth_token_getters
        self._pre_hook = pre_hook
        self._post_hook = post_hook

    @override
    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        """Loads tools from the toolbox server and wraps them."""
        # Note: We don't close the client after get_tools because tools might need it.

        tools = []
        # 1. Load specific toolset if requested
        if self._toolset_name:
            core_tools = await self._client.load_toolset(
                self._toolset_name,
                bound_params=self._bound_params or {},
                auth_token_getters=self._auth_token_getters or {},
            )
            tools.extend(core_tools)

        # 2. Load specific tools if requested
        if self._tool_names:
            for name in self._tool_names:
                core_tool = await self._client.load_tool(
                    name,
                    bound_params=self._bound_params or {},
                    auth_token_getters=self._auth_token_getters or {},
                )
                tools.append(core_tool)

        # 3. If NO tools/toolsets were specified, default to loading everything (default toolset)
        if not self._toolset_name and not self._tool_names:
            core_tools = await self._client.load_toolset(
                None,
                bound_params=self._bound_params or {},
                auth_token_getters=self._auth_token_getters or {},
            )
            tools.extend(core_tools)

        # Wrap all core tools in ToolboxTool
        return [
            ToolboxTool(
                core_tool=t,
                pre_hook=self._pre_hook,
                post_hook=self._post_hook,
                auth_config=self._client.credential_config,
            )
            for t in tools
        ]

    async def close(self):
        await self._client.close()
