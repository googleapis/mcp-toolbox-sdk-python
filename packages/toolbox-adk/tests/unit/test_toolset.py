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


from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from toolbox_core.protocol import Protocol

from toolbox_adk.tool import ToolboxTool
from toolbox_adk.toolset import ToolboxToolset


class TestToolboxToolset:

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_get_tools_load_set_and_list(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        # Setup mocks returning list of tools
        t1 = MagicMock()
        t1.__name__ = "tool1"
        t1.__doc__ = "desc1"
        t2 = MagicMock()
        t2.__name__ = "tool2"
        t2.__doc__ = "desc2"
        mock_client.load_toolset = AsyncMock(return_value=[t1])
        mock_client.load_tool = AsyncMock(return_value=t2)

        toolset = ToolboxToolset(
            "url", toolset_name="set1", tool_names=["toolA"], bound_params={"p": 1}
        )

        tools = await toolset.get_tools()

        assert len(tools) == 2
        assert isinstance(tools[0], ToolboxTool)
        assert isinstance(tools[1], ToolboxTool)

        mock_client.load_toolset.assert_awaited_with(
            "set1", bound_params={"p": 1}, auth_token_getters={}
        )
        mock_client.load_tool.assert_awaited_with(
            "toolA", bound_params={"p": 1}, auth_token_getters={}
        )

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_get_tools_with_auth_token_getters(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        # Setup mocks
        t1 = MagicMock()
        t1.__name__ = "tool1"
        t1.__doc__ = "desc1"
        mock_client.load_tool = AsyncMock(return_value=t1)

        auth_getters = {"service": lambda: "token"}
        toolset = ToolboxToolset(
            "url", tool_names=["toolA"], auth_token_getters=auth_getters
        )

        tools = await toolset.get_tools()

        assert len(tools) == 1
        mock_client.load_tool.assert_awaited_with(
            "toolA", bound_params={}, auth_token_getters=auth_getters
        )

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_hooks_propagation(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        t1 = MagicMock()
        t1.__name__ = "tool1"
        t1.__doc__ = "desc1"
        mock_client.load_toolset = AsyncMock(return_value=[t1])

        hook = AsyncMock()
        toolset = ToolboxToolset("url", toolset_name="s", pre_hook=hook)

        tools = await toolset.get_tools()
        assert tools[0]._pre_hook == hook

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_close(self, mock_client_cls):
        mock_instance = mock_client_cls.return_value
        mock_instance.close = AsyncMock()

        toolset = ToolboxToolset("url")
        # Access client to trigger lazy creation
        _ = toolset.client
        await toolset.close()
        mock_instance.close.assert_awaited()

    @patch("toolbox_adk.toolset.ToolboxClient")
    def test_init_with_protocol(self, mock_client_cls):
        """Test that protocol argument is passed to the client."""
        toolset = ToolboxToolset("url", protocol=Protocol.MCP)
        # Access client to trigger init
        _ = toolset.client
        
        mock_client_cls.assert_called_once()
        call_kwargs = mock_client_cls.call_args[1]
        assert call_kwargs["protocol"] == Protocol.MCP

