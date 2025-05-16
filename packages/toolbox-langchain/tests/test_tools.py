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
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from pydantic import BaseModel
from toolbox_core.protocol import ParameterSchema as CoreParameterSchema
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool
from toolbox_core.tool import ToolboxTool as CoreAsyncTool
from toolbox_core.utils import params_to_pydantic_model

from toolbox_langchain.tools import ToolboxTool


def assert_pydantic_models_equivalent(
    model_cls1: type[BaseModel], model_cls2: type[BaseModel], expected_model_name: str
):
    assert issubclass(model_cls1, BaseModel), "model_cls1 is not a Pydantic BaseModel"
    assert issubclass(model_cls2, BaseModel), "model_cls2 is not a Pydantic BaseModel"
    assert (
        model_cls1.__name__ == expected_model_name
    ), f"model_cls1 name mismatch: expected {expected_model_name}, got {model_cls1.__name__}"
    assert (
        model_cls2.__name__ == expected_model_name
    ), f"model_cls2 name mismatch: expected {expected_model_name}, got {model_cls2.__name__}"

    fields1 = model_cls1.model_fields
    fields2 = model_cls2.model_fields

    assert (
        fields1.keys() == fields2.keys()
    ), f"Field names mismatch: {fields1.keys()} != {fields2.keys()}"

    for field_name in fields1.keys():
        field_info1 = fields1[field_name]
        field_info2 = fields2[field_name]

        assert (
            field_info1.annotation == field_info2.annotation
        ), f"Field '{field_name}': Annotation mismatch ({field_info1.annotation} != {field_info2.annotation})"
        assert (
            field_info1.description == field_info2.description
        ), f"Field '{field_name}': Description mismatch ('{field_info1.description}' != '{field_info2.description}')"
        is_required1 = (
            field_info1.is_required()
            if hasattr(field_info1, "is_required")
            else not field_info1.is_nullable()
        )
        is_required2 = (
            field_info2.is_required()
            if hasattr(field_info2, "is_required")
            else not field_info2.is_nullable()
        )
        assert (
            is_required1 == is_required2
        ), f"Field '{field_name}': Required status mismatch ({is_required1} != {is_required2})"


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

    @pytest.fixture
    def mock_core_tool(self, tool_schema_dict):
        sync_mock = Mock(spec=ToolboxCoreSyncTool)

        sync_mock.__name__ = "test_tool_name_for_langchain"
        sync_mock.__doc__ = tool_schema_dict["description"]
        sync_mock._name = "TestToolPydanticModel"
        sync_mock._params = [
            CoreParameterSchema(**p) for p in tool_schema_dict["parameters"]
        ]

        mock_async_tool_attr = AsyncMock(spec=CoreAsyncTool)
        mock_async_tool_attr.return_value = "dummy_internal_async_tool_result"
        sync_mock._ToolboxSyncTool__async_tool = mock_async_tool_attr
        sync_mock._ToolboxSyncTool__loop = Mock(spec=asyncio.AbstractEventLoop)
        sync_mock._ToolboxSyncTool__thread = Mock()

        new_mock_instance_for_methods = Mock(spec=ToolboxCoreSyncTool)
        new_mock_instance_for_methods.__name__ = sync_mock.__name__
        new_mock_instance_for_methods.__doc__ = sync_mock.__doc__
        new_mock_instance_for_methods._name = sync_mock._name
        new_mock_instance_for_methods._params = sync_mock._params
        new_mock_instance_for_methods._ToolboxSyncTool__async_tool = AsyncMock(
            spec=CoreAsyncTool
        )
        new_mock_instance_for_methods._ToolboxSyncTool__loop = Mock(
            spec=asyncio.AbstractEventLoop
        )
        new_mock_instance_for_methods._ToolboxSyncTool__thread = Mock()

        sync_mock.add_auth_token_getters = Mock(
            return_value=new_mock_instance_for_methods
        )
        sync_mock.bind_params = Mock(return_value=new_mock_instance_for_methods)

        return sync_mock

    @pytest.fixture
    def mock_core_sync_auth_tool(self, auth_tool_schema_dict):
        sync_mock = Mock(spec=ToolboxCoreSyncTool)
        sync_mock.__name__ = "test_auth_tool_lc_name"
        sync_mock.__doc__ = auth_tool_schema_dict["description"]
        sync_mock._name = "TestAuthToolPydanticModel"
        sync_mock._params = [
            CoreParameterSchema(**p) for p in auth_tool_schema_dict["parameters"]
        ]

        mock_async_tool_attr = AsyncMock(spec=CoreAsyncTool)
        mock_async_tool_attr.return_value = "dummy_internal_async_auth_tool_result"
        sync_mock._ToolboxSyncTool__async_tool = mock_async_tool_attr
        sync_mock._ToolboxSyncTool__loop = Mock(spec=asyncio.AbstractEventLoop)
        sync_mock._ToolboxSyncTool__thread = Mock()

        new_mock_instance_for_methods = Mock(spec=ToolboxCoreSyncTool)
        new_mock_instance_for_methods.__name__ = sync_mock.__name__
        new_mock_instance_for_methods.__doc__ = sync_mock.__doc__
        new_mock_instance_for_methods._name = sync_mock._name
        new_mock_instance_for_methods._params = sync_mock._params
        new_mock_instance_for_methods._ToolboxSyncTool__async_tool = AsyncMock(
            spec=CoreAsyncTool
        )
        new_mock_instance_for_methods._ToolboxSyncTool__loop = Mock(
            spec=asyncio.AbstractEventLoop
        )
        new_mock_instance_for_methods._ToolboxSyncTool__thread = Mock()

        sync_mock.add_auth_token_getters = Mock(
            return_value=new_mock_instance_for_methods
        )
        sync_mock.bind_params = Mock(return_value=new_mock_instance_for_methods)
        return sync_mock

    @pytest.fixture
    def toolbox_tool(self, mock_core_tool):
        return ToolboxTool(core_tool=mock_core_tool)

    @pytest.fixture
    def auth_toolbox_tool(self, mock_core_sync_auth_tool):
        return ToolboxTool(core_tool=mock_core_sync_auth_tool)

    def test_toolbox_tool_init(self, mock_core_tool):
        tool = ToolboxTool(core_tool=mock_core_tool)

        assert tool.name == mock_core_tool.__name__
        assert tool.description == mock_core_tool.__doc__
        assert tool._ToolboxTool__core_tool == mock_core_tool

        expected_args_schema = params_to_pydantic_model(
            mock_core_tool._name, mock_core_tool._params
        )
        assert_pydantic_models_equivalent(
            tool.args_schema, expected_args_schema, mock_core_tool._name
        )

    @pytest.mark.parametrize(
        "params",
        [
            ({"param1": "bound-value"}),
            ({"param1": lambda: "bound-value"}),
            ({"param1": "bound-value", "param2": 123}),
        ],
    )
    def test_toolbox_tool_bind_params(
        self,
        params,
        toolbox_tool,
        mock_core_tool,
    ):
        returned_core_tool_mock = mock_core_tool.bind_params.return_value
        new_langchain_tool = toolbox_tool.bind_params(params)

        mock_core_tool.bind_params.assert_called_once_with(params)
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert new_langchain_tool._ToolboxTool__core_tool == returned_core_tool_mock

    def test_toolbox_tool_bind_param(self, toolbox_tool, mock_core_tool):
        returned_core_tool_mock = mock_core_tool.bind_params.return_value
        new_langchain_tool = toolbox_tool.bind_param("param1", "bound-value")

        mock_core_tool.bind_params.assert_called_once_with({"param1": "bound-value"})
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert new_langchain_tool._ToolboxTool__core_tool == returned_core_tool_mock

    @pytest.mark.parametrize(
        "auth_token_getters",
        [
            ({"test-auth-source": lambda: "test-token"}),
            (
                {
                    "test-auth-source": lambda: "test-token",
                    "another-auth-source": lambda: "another-token",
                }
            ),
        ],
    )
    def test_toolbox_tool_add_auth_token_getters(
        self,
        auth_token_getters,
        auth_toolbox_tool,
        mock_core_sync_auth_tool,
    ):
        returned_core_tool_mock = (
            mock_core_sync_auth_tool.add_auth_token_getters.return_value
        )
        new_langchain_tool = auth_toolbox_tool.add_auth_token_getters(
            auth_token_getters
        )

        mock_core_sync_auth_tool.add_auth_token_getters.assert_called_once_with(
            auth_token_getters
        )
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert new_langchain_tool._ToolboxTool__core_tool == returned_core_tool_mock

    def test_toolbox_tool_add_auth_token_getter(
        self, auth_toolbox_tool, mock_core_sync_auth_tool
    ):
        get_id_token = lambda: "test-token"
        returned_core_tool_mock = (
            mock_core_sync_auth_tool.add_auth_token_getters.return_value
        )

        new_langchain_tool = auth_toolbox_tool.add_auth_token_getter(
            "test-auth-source", get_id_token
        )

        mock_core_sync_auth_tool.add_auth_token_getters.assert_called_once_with(
            {"test-auth-source": get_id_token}
        )
        assert isinstance(new_langchain_tool, ToolboxTool)
        assert new_langchain_tool._ToolboxTool__core_tool == returned_core_tool_mock

    def test_toolbox_tool_run(self, toolbox_tool, mock_core_tool):
        kwargs_to_run = {"param1": "run_value1", "param2": 100}
        expected_result = "sync_run_output"
        mock_core_tool.return_value = expected_result

        result = toolbox_tool._run(**kwargs_to_run)

        assert result == expected_result
        assert mock_core_tool.call_count == 1
        assert mock_core_tool.call_args == call(**kwargs_to_run)

    @pytest.mark.asyncio
    @patch("toolbox_langchain.tools.to_thread", new_callable=AsyncMock)
    async def test_toolbox_tool_arun(
        self, mock_to_thread_in_tools, toolbox_tool, mock_core_tool
    ):
        kwargs_to_run = {"param1": "arun_value1", "param2": 200}
        expected_result = "async_run_output"

        mock_core_tool.return_value = expected_result

        async def to_thread_side_effect(func, *args, **kwargs_for_func):
            return func(**kwargs_for_func)

        mock_to_thread_in_tools.side_effect = to_thread_side_effect

        result = await toolbox_tool._arun(**kwargs_to_run)

        assert result == expected_result
        mock_to_thread_in_tools.assert_awaited_once_with(
            mock_core_tool, **kwargs_to_run
        )

        assert mock_core_tool.call_count == 1
        assert mock_core_tool.call_args == call(**kwargs_to_run)
