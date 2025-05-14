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

from unittest.mock import Mock

import pytest
from pydantic import BaseModel
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool

from toolbox_langchain.tools import ToolboxTool


class TestToolboxTool:
    @pytest.fixture
    def tool_schema_dict(self):
        return {
            "description": "Test Tool Description",
            "parameters": [
                {"name": "param1", "type": "string", "description": "Param 1"},
                {"name": "param2", "type": "integer", "description": "Param 2"},
            ],
        }

    @pytest.fixture
    def auth_tool_schema_dict(self):
        return {
            "description": "Test Auth Tool Description",
            "authRequired": ["test-auth-source"],
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "Param 1",
                    "authSources": ["test-auth-source"],
                },
                {"name": "param2", "type": "integer", "description": "Param 2"},
            ],
        }

    @pytest.fixture(scope="function")
    def mock_core_async_tool(self, tool_schema_dict):
        mock = Mock(spec=ToolboxCoreTool)
        mock.__name__ = "test_tool"
        mock.__doc__ = tool_schema_dict["description"]
        mock._pydantic_model = BaseModel
        return mock

    @pytest.fixture(scope="function")
    def mock_core_async_auth_tool(self, auth_tool_schema_dict):
        mock = Mock(spec=ToolboxCoreTool)
        mock.__name__ = "test_auth_tool"
        mock.__doc__ = auth_tool_schema_dict["description"]
        mock._pydantic_model = BaseModel
        return mock

    @pytest.fixture
    def mock_core_tool(self, mock_core_async_tool):
        sync_mock = Mock(spec=ToolboxCoreSyncTool)
        sync_mock.__name__ = mock_core_async_tool.__name__
        sync_mock.__doc__ = mock_core_async_tool.__doc__
        sync_mock._async_tool = mock_core_async_tool
        sync_mock.add_auth_token_getters = Mock(return_value=sync_mock)
        sync_mock.bind_params = Mock(return_value=sync_mock)
        sync_mock.bind_param = Mock(
            return_value=sync_mock
        )  # Keep this if bind_param exists on core, otherwise remove
        sync_mock.__call__ = Mock(return_value="mocked_sync_call_result")
        return sync_mock

    @pytest.fixture
    def mock_core_sync_auth_tool(self, mock_core_async_auth_tool):
        sync_mock = Mock(spec=ToolboxCoreSyncTool)
        sync_mock.__name__ = mock_core_async_auth_tool.__name__
        sync_mock.__doc__ = mock_core_async_auth_tool.__doc__
        sync_mock._async_tool = mock_core_async_auth_tool
        sync_mock.add_auth_token_getters = Mock(return_value=sync_mock)
        sync_mock.bind_params = Mock(return_value=sync_mock)
        sync_mock.bind_param = Mock(
            return_value=sync_mock
        )  # Keep this if bind_param exists on core
        sync_mock.__call__ = Mock(return_value="mocked_auth_sync_call_result")
        return sync_mock

    @pytest.fixture
    def toolbox_tool(self, mock_core_tool):
        return ToolboxTool(core_tool=mock_core_tool)

    @pytest.fixture
    def auth_toolbox_tool(self, mock_core_sync_auth_tool):
        return ToolboxTool(core_tool=mock_core_sync_auth_tool)

    def test_toolbox_tool_init(self, mock_core_tool):
        tool = ToolboxTool(core_tool=mock_core_tool)
        core_tool_in_tool = tool._ToolboxTool__core_tool
        assert core_tool_in_tool.__name__ == mock_core_tool.__name__
        assert core_tool_in_tool.__doc__ == mock_core_tool.__doc__
        assert tool.args_schema == mock_core_tool._async_tool._pydantic_model

    @pytest.mark.parametrize(
        "params, expected_bound_params_on_core",
        [
            ({"param1": "bound-value"}, {"param1": "bound-value"}),
            ({"param1": lambda: "bound-value"}, {"param1": lambda: "bound-value"}),
            (
                {"param1": "bound-value", "param2": 123},
                {"param1": "bound-value", "param2": 123},
            ),
        ],
    )
    def test_toolbox_tool_bind_params(
        self,
        params,
        expected_bound_params_on_core,
        toolbox_tool,
        mock_core_tool,
    ):
        mock_core_tool.bind_params.return_value = mock_core_tool
        new_langchain_tool = toolbox_tool.bind_params(params)
        mock_core_tool.bind_params.assert_called_once_with(params)
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert (
            new_langchain_tool._ToolboxTool__core_tool
            == mock_core_tool.bind_params.return_value
        )

    def test_toolbox_tool_bind_param(self, toolbox_tool, mock_core_tool):
        # ToolboxTool.bind_param calls core_tool.bind_params
        mock_core_tool.bind_params.return_value = mock_core_tool
        new_langchain_tool = toolbox_tool.bind_param("param1", "bound-value")
        # *** Fix: Assert that bind_params is called on the core tool ***
        mock_core_tool.bind_params.assert_called_once_with({"param1": "bound-value"})
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert (
            new_langchain_tool._ToolboxTool__core_tool
            == mock_core_tool.bind_params.return_value
        )

    @pytest.mark.parametrize(
        "auth_token_getters, expected_auth_getters_on_core",
        [
            (
                {"test-auth-source": lambda: "test-token"},
                {"test-auth-source": lambda: "test-token"},
            ),
            (
                {
                    "test-auth-source": lambda: "test-token",
                    "another-auth-source": lambda: "another-token",
                },
                {
                    "test-auth-source": lambda: "test-token",
                    "another-auth-source": lambda: "another-token",
                },
            ),
        ],
    )
    def test_toolbox_tool_add_auth_token_getters(
        self,
        auth_token_getters,
        expected_auth_getters_on_core,
        auth_toolbox_tool,
        mock_core_sync_auth_tool,
    ):
        mock_core_sync_auth_tool.add_auth_token_getters.return_value = (
            mock_core_sync_auth_tool
        )
        new_langchain_tool = auth_toolbox_tool.add_auth_token_getters(
            auth_token_getters
        )
        mock_core_sync_auth_tool.add_auth_token_getters.assert_called_once_with(
            auth_token_getters
        )
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert (
            new_langchain_tool._ToolboxTool__core_tool
            == mock_core_sync_auth_tool.add_auth_token_getters.return_value
        )

    def test_toolbox_tool_add_auth_token_getter(
        self, auth_toolbox_tool, mock_core_sync_auth_tool
    ):
        get_id_token = lambda: "test-token"
        # ToolboxTool.add_auth_token_getter calls core_tool.add_auth_token_getters
        mock_core_sync_auth_tool.add_auth_token_getters.return_value = (
            mock_core_sync_auth_tool
        )

        new_langchain_tool = auth_toolbox_tool.add_auth_token_getter(
            "test-auth-source", get_id_token
        )

        # *** Fix: Assert that add_auth_token_getters is called on the core tool ***
        mock_core_sync_auth_tool.add_auth_token_getters.assert_called_once_with(
            {"test-auth-source": get_id_token}
        )
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert (
            new_langchain_tool._ToolboxTool__core_tool
            == mock_core_sync_auth_tool.add_auth_token_getters.return_value
        )
