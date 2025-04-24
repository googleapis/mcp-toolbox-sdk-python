# Copyright 2024 Google LLC
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

from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel

from toolbox_llamaindex.async_tools import AsyncToolboxTool
from toolbox_llamaindex.client import ToolboxClient
from toolbox_llamaindex.tools import ToolboxTool
from toolbox_llamaindex.utils import _schema_to_model

URL = "http://test_url"


class TestToolboxClient:
    @pytest.fixture
    def tool_schema(self):
        return {
            "description": "Test Tool Description",
            "parameters": [
                {"name": "param1", "type": "string", "description": "Param 1"},
                {"name": "param2", "type": "integer", "description": "Param 2"},
            ],
        }

    @pytest.fixture()
    def toolbox_client(self):
        client = ToolboxClient(URL)
        assert isinstance(client, ToolboxClient)
        assert client._ToolboxClient__async_client is not None

        # Check that the background loop was created and started
        assert client._ToolboxClient__loop is not None
        assert client._ToolboxClient__loop.is_running()

        return client

    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_tool")
    def test_load_tool(
        self, mock_aload_tool, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool = Mock(spec=AsyncToolboxTool)
        mock_async_tool._AsyncToolboxTool__name = "mock-tool"  # Access the mangled name
        mock_async_tool._AsyncToolboxTool__schema = (
            tool_schema  # Access the mangled name
        )
        mock_aload_tool.return_value = mock_async_tool

        tool = toolbox_client.load_tool("test_tool")
        mock_toolbox_tool_init.assert_called_once_with(
            mock_async_tool,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        assert (
            tool_schema["description"]
            == mock_async_tool._AsyncToolboxTool__schema["description"]
        )
        mock_aload_tool.assert_called_once_with("test_tool", {}, None, {}, True)

    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_toolset")
    def test_load_toolset(
        self, mock_aload_toolset, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool1 = Mock(spec=AsyncToolboxTool)
        mock_async_tool1._AsyncToolboxTool__name = "mock-tool-0"
        mock_async_tool1._AsyncToolboxTool__schema = tool_schema

        mock_async_tool2 = Mock(spec=AsyncToolboxTool)
        mock_async_tool2._AsyncToolboxTool__name = "mock-tool-1"
        mock_async_tool2._AsyncToolboxTool__schema = tool_schema
        mock_aload_toolset.return_value = [mock_async_tool1, mock_async_tool2]

        tools = toolbox_client.load_toolset()
        assert len(tools) == 2
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool1,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool2,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        mock_aload_toolset.assert_called_once_with(None, {}, None, {}, True)

    @pytest.mark.asyncio
    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_tool")
    async def test_aload_tool(
        self, mock_aload_tool, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool = Mock(spec=AsyncToolboxTool)
        mock_async_tool._AsyncToolboxTool__name = "mock-tool"  # Access mangled name
        mock_async_tool._AsyncToolboxTool__schema = tool_schema
        mock_aload_tool.return_value = mock_async_tool

        tool = await toolbox_client.aload_tool("test_tool")
        mock_toolbox_tool_init.assert_called_once_with(
            mock_async_tool,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        assert (
            tool_schema["description"]
            == mock_async_tool._AsyncToolboxTool__schema["description"]
        )
        mock_aload_tool.assert_called_once_with("test_tool", {}, None, {}, True)

    @pytest.mark.asyncio
    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_toolset")
    async def test_aload_toolset(
        self, mock_aload_toolset, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool1 = Mock(spec=AsyncToolboxTool)
        mock_async_tool1._AsyncToolboxTool__name = "mock-tool-0"
        mock_async_tool1._AsyncToolboxTool__schema = tool_schema

        mock_async_tool2 = Mock(spec=AsyncToolboxTool)
        mock_async_tool2._AsyncToolboxTool__name = "mock-tool-1"
        mock_async_tool2._AsyncToolboxTool__schema = tool_schema

        mock_aload_toolset.return_value = [mock_async_tool1, mock_async_tool2]

        tools = await toolbox_client.aload_toolset()
        assert len(tools) == 2
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool1,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool2,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )
        mock_aload_toolset.assert_called_once_with(None, {}, None, {}, True)

    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_tool")
    def test_load_tool_with_args(
        self, mock_aload_tool, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool = Mock(spec=AsyncToolboxTool)
        mock_async_tool._AsyncToolboxTool__name = "mock-tool"
        mock_async_tool._AsyncToolboxTool__schema = tool_schema
        mock_aload_tool.return_value = mock_async_tool

        auth_tokens = {"token1": lambda: "value1"}
        auth_headers = {"header1": lambda: "value2"}
        bound_params = {"param1": "value3"}

        tool = toolbox_client.load_tool(
            "test_tool_name",
            auth_tokens=auth_tokens,
            auth_headers=auth_headers,
            bound_params=bound_params,
            strict=False,
        )
        mock_toolbox_tool_init.assert_called_once_with(
            mock_async_tool,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        assert (
            tool_schema["description"]
            == mock_async_tool._AsyncToolboxTool__schema["description"]
        )
        mock_aload_tool.assert_called_once_with(
            "test_tool_name", auth_tokens, auth_headers, bound_params, False
        )

    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_toolset")
    def test_load_toolset_with_args(
        self, mock_aload_toolset, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool1 = Mock(spec=AsyncToolboxTool)
        mock_async_tool1._AsyncToolboxTool__name = "mock-tool-0"
        mock_async_tool1._AsyncToolboxTool__schema = tool_schema

        mock_async_tool2 = Mock(spec=AsyncToolboxTool)
        mock_async_tool2._AsyncToolboxTool__name = "mock-tool-1"
        mock_async_tool2._AsyncToolboxTool__schema = tool_schema

        mock_aload_toolset.return_value = [mock_async_tool1, mock_async_tool2]

        auth_tokens = {"token1": lambda: "value1"}
        auth_headers = {"header1": lambda: "value2"}
        bound_params = {"param1": "value3"}

        tools = toolbox_client.load_toolset(
            toolset_name="my_toolset",
            auth_tokens=auth_tokens,
            auth_headers=auth_headers,
            bound_params=bound_params,
            strict=False,
        )

        assert len(tools) == 2
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool1,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool2,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        mock_aload_toolset.assert_called_once_with(
            "my_toolset", auth_tokens, auth_headers, bound_params, False
        )

    @pytest.mark.asyncio
    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_tool")
    async def test_aload_tool_with_args(
        self, mock_aload_tool, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool = Mock(spec=AsyncToolboxTool)
        mock_async_tool._AsyncToolboxTool__name = "mock-tool"
        mock_async_tool._AsyncToolboxTool__schema = tool_schema
        mock_aload_tool.return_value = mock_async_tool

        auth_tokens = {"token1": lambda: "value1"}
        auth_headers = {"header1": lambda: "value2"}
        bound_params = {"param1": "value3"}

        tool = await toolbox_client.aload_tool(
            "test_tool", auth_tokens, auth_headers, bound_params, False
        )
        mock_toolbox_tool_init.assert_called_once_with(
            mock_async_tool,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        assert (
            tool_schema["description"]
            == mock_async_tool._AsyncToolboxTool__schema["description"]
        )
        mock_aload_tool.assert_called_once_with(
            "test_tool", auth_tokens, auth_headers, bound_params, False
        )

    @pytest.mark.asyncio
    @patch("toolbox_llamaindex.client.ToolboxTool.__init__", return_value=None)
    @patch("toolbox_llamaindex.client.AsyncToolboxClient.aload_toolset")
    async def test_aload_toolset_with_args(
        self, mock_aload_toolset, mock_toolbox_tool_init, toolbox_client, tool_schema
    ):
        mock_async_tool1 = Mock(spec=AsyncToolboxTool)
        mock_async_tool1._AsyncToolboxTool__name = "mock-tool-0"
        mock_async_tool1._AsyncToolboxTool__schema = tool_schema

        mock_async_tool2 = Mock(spec=AsyncToolboxTool)
        mock_async_tool2._AsyncToolboxTool__name = "mock-tool-1"
        mock_async_tool2._AsyncToolboxTool__schema = tool_schema
        mock_aload_toolset.return_value = [mock_async_tool1, mock_async_tool2]

        auth_tokens = {"token1": lambda: "value1"}
        auth_headers = {"header1": lambda: "value2"}
        bound_params = {"param1": "value3"}

        tools = await toolbox_client.aload_toolset(
            "my_toolset", auth_tokens, auth_headers, bound_params, False
        )
        assert len(tools) == 2
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool1,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )
        mock_toolbox_tool_init.assert_any_call(
            mock_async_tool2,
            toolbox_client._ToolboxClient__loop,
            toolbox_client._ToolboxClient__thread,
        )

        mock_aload_toolset.assert_called_once_with(
            "my_toolset", auth_tokens, auth_headers, bound_params, False
        )
