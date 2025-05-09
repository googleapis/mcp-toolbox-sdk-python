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

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool  # For spec
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool  # For spec

from toolbox_langchain.client import ToolboxClient
from toolbox_langchain.tools import ToolboxTool

URL = "http://test_url"


class TestToolboxClient:
    @pytest.fixture()
    def toolbox_client(self):
        client = ToolboxClient(URL)
        assert isinstance(client, ToolboxClient)
        assert client._ToolboxClient__core_sync_client is not None
        assert client._ToolboxClient__core_sync_client._async_client is not None
        assert client._ToolboxClient__core_sync_client._loop is not None
        assert client._ToolboxClient__core_sync_client._loop.is_running()
        assert client._ToolboxClient__core_sync_client._thread is not None
        assert client._ToolboxClient__core_sync_client._thread.is_alive()
        return client

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    def test_load_tool(self, mock_core_load_tool, toolbox_client):
        mock_core_sync_tool_instance = Mock(
            spec=ToolboxCoreSyncTool
        )  # Spec with Core Sync Tool
        mock_core_sync_tool_instance.__name__ = "mock-core-sync-tool"
        mock_core_sync_tool_instance.__doc__ = "mock core sync description"

        mock_underlying_async_tool = Mock(
            spec=ToolboxCoreTool
        )  # Core Async Tool for pydantic model
        mock_underlying_async_tool._pydantic_model = BaseModel
        mock_core_sync_tool_instance._async_tool = mock_underlying_async_tool

        mock_core_load_tool.return_value = mock_core_sync_tool_instance

        langchain_tool = toolbox_client.load_tool("test_tool")

        assert isinstance(langchain_tool, ToolboxTool)
        assert langchain_tool.name == mock_core_sync_tool_instance.__name__
        assert langchain_tool.description == mock_core_sync_tool_instance.__doc__
        assert langchain_tool.args_schema == mock_underlying_async_tool._pydantic_model

        mock_core_load_tool.assert_called_once_with(
            name="test_tool", auth_token_getters={}, bound_params={}
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    def test_load_toolset(self, mock_core_load_toolset, toolbox_client):
        mock_core_sync_tool_instance1 = Mock(spec=ToolboxCoreSyncTool)
        mock_core_sync_tool_instance1.__name__ = "mock-core-sync-tool-0"
        mock_core_sync_tool_instance1.__doc__ = "desc 0"
        mock_async_tool0 = Mock(spec=ToolboxCoreTool)
        mock_async_tool0._pydantic_model = BaseModel
        mock_core_sync_tool_instance1._async_tool = mock_async_tool0

        mock_core_sync_tool_instance2 = Mock(spec=ToolboxCoreSyncTool)
        mock_core_sync_tool_instance2.__name__ = "mock-core-sync-tool-1"
        mock_core_sync_tool_instance2.__doc__ = "desc 1"
        mock_async_tool1 = Mock(spec=ToolboxCoreTool)
        mock_async_tool1._pydantic_model = BaseModel
        mock_core_sync_tool_instance2._async_tool = mock_async_tool1

        mock_core_load_toolset.return_value = [
            mock_core_sync_tool_instance1,
            mock_core_sync_tool_instance2,
        ]

        langchain_tools = toolbox_client.load_toolset()
        assert len(langchain_tools) == 2
        assert isinstance(langchain_tools[0], ToolboxTool)
        assert isinstance(langchain_tools[1], ToolboxTool)
        assert langchain_tools[0].name == "mock-core-sync-tool-0"
        assert langchain_tools[1].name == "mock-core-sync-tool-1"

        mock_core_load_toolset.assert_called_once_with(
            name=None, auth_token_getters={}, bound_params={}, strict=False
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.client.ToolboxClient.load_tool")
    async def test_aload_tool(self, mock_core_aload_tool, toolbox_client):
        mock_core_tool_instance = AsyncMock(
            spec=ToolboxCoreTool
        )  # *** Use AsyncMock for async method return ***
        mock_core_tool_instance.__name__ = "mock-core-async-tool"
        mock_core_tool_instance.__doc__ = "mock core async description"
        mock_core_tool_instance._pydantic_model = BaseModel
        mock_core_aload_tool.return_value = mock_core_tool_instance

        langchain_tool = await toolbox_client.aload_tool("test_tool")

        assert isinstance(langchain_tool, ToolboxTool)
        assert langchain_tool.name == mock_core_tool_instance.__name__
        assert langchain_tool.description == mock_core_tool_instance.__doc__

        toolbox_client._ToolboxClient__core_sync_client._async_client.load_tool.assert_called_once_with(
            name="test_tool", auth_token_getters={}, bound_params={}
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.client.ToolboxClient.load_toolset")
    async def test_aload_toolset(self, mock_core_aload_toolset, toolbox_client):
        mock_core_tool_instance1 = AsyncMock(
            spec=ToolboxCoreTool
        )  # *** Use AsyncMock ***
        mock_core_tool_instance1.__name__ = "mock-core-async-tool-0"
        mock_core_tool_instance1.__doc__ = "desc 0"
        mock_core_tool_instance1._pydantic_model = BaseModel

        mock_core_tool_instance2 = AsyncMock(
            spec=ToolboxCoreTool
        )  # *** Use AsyncMock ***
        mock_core_tool_instance2.__name__ = "mock-core-async-tool-1"
        mock_core_tool_instance2.__doc__ = "desc 1"
        mock_core_tool_instance2._pydantic_model = BaseModel

        mock_core_aload_toolset.return_value = [
            mock_core_tool_instance1,
            mock_core_tool_instance2,
        ]

        langchain_tools = await toolbox_client.aload_toolset()
        assert len(langchain_tools) == 2
        assert isinstance(langchain_tools[0], ToolboxTool)
        assert isinstance(langchain_tools[1], ToolboxTool)

        toolbox_client._ToolboxClient__core_sync_client._async_client.load_toolset.assert_called_once_with(
            name=None, auth_token_getters={}, bound_params={}, strict=False
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    def test_load_tool_with_args(self, mock_core_load_tool, toolbox_client):
        mock_core_sync_tool_instance = Mock(spec=ToolboxCoreSyncTool)
        mock_core_sync_tool_instance.__name__ = "mock-tool"
        mock_async_tool = Mock(spec=ToolboxCoreTool)
        mock_async_tool._pydantic_model = BaseModel
        mock_core_sync_tool_instance._async_tool = mock_async_tool
        mock_core_load_tool.return_value = mock_core_sync_tool_instance

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}

        # Test case where auth_token_getters takes precedence
        with pytest.warns(DeprecationWarning) as record:
            tool = toolbox_client.load_tool(
                "test_tool_name",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        # Expect two warnings: one for auth_tokens, one for auth_headers
        assert len(record) == 2
        messages = [str(r.message) for r in record]
        assert any("auth_tokens` is deprecated" in m for m in messages)
        assert any("auth_headers` is deprecated" in m for m in messages)

        assert isinstance(tool, ToolboxTool)
        mock_core_load_tool.assert_called_with(  # Use called_with for flexibility if called multiple times in setup
            name="test_tool_name",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
        )
        mock_core_load_tool.reset_mock()  # Reset for next test case

        # Test case where auth_tokens is used (auth_token_getters is None)
        with pytest.warns(DeprecationWarning, match="auth_tokens` is deprecated"):
            toolbox_client.load_tool(
                "test_tool_name_2",
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,  # This will also warn
                bound_params=bound_params,
            )
        mock_core_load_tool.assert_called_with(
            name="test_tool_name_2",
            auth_token_getters=auth_tokens_deprecated,  # auth_tokens becomes auth_token_getters
            bound_params=bound_params,
        )
        mock_core_load_tool.reset_mock()

        # Test case where auth_headers is used (auth_token_getters and auth_tokens are None)
        with pytest.warns(DeprecationWarning, match="auth_headers` is deprecated"):
            toolbox_client.load_tool(
                "test_tool_name_3",
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        mock_core_load_tool.assert_called_with(
            name="test_tool_name_3",
            auth_token_getters=auth_headers_deprecated,  # auth_headers becomes auth_token_getters
            bound_params=bound_params,
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    def test_load_toolset_with_args(self, mock_core_load_toolset, toolbox_client):
        mock_core_sync_tool_instance = Mock(spec=ToolboxCoreSyncTool)
        mock_core_sync_tool_instance.__name__ = "mock-tool-0"
        mock_async_tool = Mock(spec=ToolboxCoreTool)
        mock_async_tool._pydantic_model = BaseModel
        mock_core_sync_tool_instance._async_tool = mock_async_tool
        mock_core_load_toolset.return_value = [mock_core_sync_tool_instance]

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}

        with pytest.warns(DeprecationWarning) as record:  # Expect 2 warnings
            tools = toolbox_client.load_toolset(
                toolset_name="my_toolset",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
                strict=False,
            )
        assert len(record) == 2
        messages = [str(r.message) for r in record]
        assert any("auth_tokens` is deprecated" in m for m in messages)
        assert any("auth_headers` is deprecated" in m for m in messages)

        assert len(tools) == 1
        mock_core_load_toolset.assert_called_with(
            name="my_toolset",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
            strict=False,
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.client.ToolboxClient.load_tool")
    async def test_aload_tool_with_args(self, mock_core_aload_tool, toolbox_client):
        mock_core_tool_instance = AsyncMock(spec=ToolboxCoreTool)
        mock_core_tool_instance.__name__ = "mock-tool"
        mock_core_tool_instance._pydantic_model = BaseModel
        mock_core_aload_tool.return_value = mock_core_tool_instance

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}

        with pytest.warns(DeprecationWarning) as record:  # Expect 2 warnings
            tool = await toolbox_client.aload_tool(
                "test_tool",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        assert len(record) == 2
        messages = [str(r.message) for r in record]
        assert any("auth_tokens` is deprecated" in m for m in messages)
        assert any("auth_headers` is deprecated" in m for m in messages)

        assert isinstance(tool, ToolboxTool)
        toolbox_client._ToolboxClient__core_sync_client._async_client.load_tool.assert_called_with(
            name="test_tool",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.client.ToolboxClient.load_toolset")
    async def test_aload_toolset_with_args(
        self, mock_core_aload_toolset, toolbox_client
    ):
        mock_core_tool_instance = AsyncMock(spec=ToolboxCoreTool)
        mock_core_tool_instance.__name__ = "mock-tool-0"
        mock_core_tool_instance._pydantic_model = BaseModel
        mock_core_aload_toolset.return_value = [mock_core_tool_instance]

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}

        with pytest.warns(DeprecationWarning) as record:  # Expect 2 warnings
            tools = await toolbox_client.aload_toolset(
                "my_toolset",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
                strict=False,
            )
        assert len(record) == 2
        messages = [str(r.message) for r in record]
        assert any("auth_tokens` is deprecated" in m for m in messages)
        assert any("auth_headers` is deprecated" in m for m in messages)

        assert len(tools) == 1
        toolbox_client._ToolboxClient__core_sync_client._async_client.load_toolset.assert_called_with(
            name="my_toolset",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
            strict=False,
        )
