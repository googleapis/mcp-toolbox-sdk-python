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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from toolbox_adk.tool import ToolboxTool
from toolbox_adk.toolset import ToolboxToolset


class TestToolboxToolset:

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_get_tools_load_set_and_list(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        # Setup mocks returning list of tools
        t1 = MagicMock()
        t2 = MagicMock()
        mock_client.load_toolset = AsyncMock(return_value=[t1])
        mock_client.load_tool = AsyncMock(return_value=t2)

        toolset = ToolboxToolset(
            "url", toolset_name="set1", tool_names=["toolA"], bound_params={"p": 1}
        )

        tools = await toolset.get_tools()

        assert len(tools) == 2
        assert isinstance(tools[0], ToolboxTool)
        assert isinstance(tools[1], ToolboxTool)

        mock_client.load_toolset.assert_awaited_with("set1", bound_params={"p": 1})
        mock_client.load_tool.assert_awaited_with("toolA", bound_params={"p": 1})

    @patch("toolbox_adk.toolset.ToolboxClient")
    @pytest.mark.asyncio
    async def test_hooks_propagation(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.load_toolset = AsyncMock(return_value=[MagicMock()])

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
        await toolset.close()
        mock_instance.close.assert_awaited()
