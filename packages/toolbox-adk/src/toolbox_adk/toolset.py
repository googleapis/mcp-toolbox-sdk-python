# Copyright 2026 Google LLC
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
from google.adk.tools.tool_context import ToolContext
from typing_extensions import override

from .client import ToolboxClient
from .credentials import CredentialConfig
from .tool import ToolboxTool


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
        pre_hook: Optional[
            Callable[[ToolContext, Dict[str, Any]], Awaitable[None]]
        ] = None,
        post_hook: Optional[
            Callable[
                [ToolContext, Dict[str, Any], Optional[Any], Optional[Exception]],
                Awaitable[None],
            ]
        ] = None,
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
        self.__server_url = server_url
        self.__credentials = credentials
        self.__additional_headers = additional_headers
        self.__kwargs = kwargs
        self.__client: Optional[ToolboxClient] = None
        
        self.__toolset_name = toolset_name
        self.__tool_names = tool_names
        self.__bound_params = bound_params
        self.__auth_token_getters = auth_token_getters
        self.__pre_hook = pre_hook
        self.__post_hook = post_hook

    @property
    def client(self) -> ToolboxClient:
        if self.__client is None:
             self.__client = ToolboxClient(
                server_url=self.__server_url,
                credentials=self.__credentials,
                additional_headers=self.__additional_headers,
                **self.__kwargs,
            )
        return self.__client

    @override
    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        """Loads tools from the toolbox server and wraps them."""
        # Note: We don't close the client after get_tools because tools might need it.

        tools = []
        # 1. Load specific toolset if requested
        if self.__toolset_name:
            core_tools = await self.client.load_toolset(
                self.__toolset_name,
                bound_params=self.__bound_params or {},
                auth_token_getters=self.__auth_token_getters or {},
            )
            tools.extend(core_tools)

        # 2. Load specific tools if requested
        if self.__tool_names:
            for name in self.__tool_names:
                core_tool = await self.client.load_tool(
                    name,
                    bound_params=self.__bound_params or {},
                    auth_token_getters=self.__auth_token_getters or {},
                )
                tools.append(core_tool)

        # 3. If NO tools/toolsets were specified, default to loading everything (default toolset)
        if not self.__toolset_name and not self.__tool_names:
            core_tools = await self.client.load_toolset(
                None,
                bound_params=self.__bound_params or {},
                auth_token_getters=self.__auth_token_getters or {},
            )
            tools.extend(core_tools)

        # Wrap all core tools in ToolboxTool
        return [
            ToolboxTool(
                core_tool=t,
                pre_hook=self.__pre_hook,
                post_hook=self.__post_hook,
                auth_config=self.client.credential_config,
            )
            for t in tools
        ]

    async def close(self):
        if self.__client:
            await self.__client.close()
