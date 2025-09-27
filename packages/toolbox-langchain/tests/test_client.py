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

from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel
from toolbox_core.protocol import ParameterSchema as CoreParameterSchema
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool
from toolbox_core.utils import params_to_pydantic_model

from toolbox_langchain.client import ToolboxClient
from toolbox_langchain.tools import ToolboxTool

URL = "http://test_url"


def create_mock_core_sync_tool(
    name="mock-sync-tool",
    doc="Mock sync description.",
    model_name="MockSyncModel",
    params=None,
):
    mock_tool = Mock(spec=ToolboxCoreSyncTool)
    mock_tool.__name__ = name
    mock_tool.__doc__ = doc
    mock_tool._name = model_name
    if params is None:
        mock_tool._params = [
            CoreParameterSchema(name="param1", type="string", description="Param 1")
        ]
    else:
        mock_tool._params = params
    return mock_tool


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


class TestToolboxClient:
    @pytest.fixture()
    def toolbox_client(self):
        client = ToolboxClient(URL)
        assert isinstance(client, ToolboxClient)
        assert client._ToolboxClient__core_client is not None
        return client

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    def test_load_tool(self, mock_core_load_tool, toolbox_client):
        mock_core_tool_instance = create_mock_core_sync_tool(
            name="test_tool_sync",
            doc="Sync tool description.",
            model_name="TestToolSyncModel",
            params=[
                CoreParameterSchema(
                    name="sp1", type="integer", description="Sync Param 1"
                )
            ],
        )
        mock_core_load_tool.return_value = mock_core_tool_instance

        langchain_tool = toolbox_client.load_tool("test_tool")

        assert isinstance(langchain_tool, ToolboxTool)
        assert langchain_tool.name == mock_core_tool_instance.__name__
        assert langchain_tool.description == mock_core_tool_instance.__doc__

        # Generate the expected schema once for comparison
        expected_args_schema = params_to_pydantic_model(
            mock_core_tool_instance._name, mock_core_tool_instance._params
        )

        assert_pydantic_models_equivalent(
            langchain_tool.args_schema,
            expected_args_schema,
            mock_core_tool_instance._name,
        )

        mock_core_load_tool.assert_called_once_with(
            name="test_tool", auth_token_getters={}, bound_params={}
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    def test_load_toolset(self, mock_core_load_toolset, toolbox_client):
        mock_core_tool_instance1 = create_mock_core_sync_tool(
            name="tool-0", doc="desc 0", model_name="T0Model"
        )
        mock_core_tool_instance2 = create_mock_core_sync_tool(
            name="tool-1", doc="desc 1", model_name="T1Model", params=[]
        )

        mock_core_load_toolset.return_value = [
            mock_core_tool_instance1,
            mock_core_tool_instance2,
        ]

        langchain_tools = toolbox_client.load_toolset()
        assert len(langchain_tools) == 2

        tool_instances_mocks = [mock_core_tool_instance1, mock_core_tool_instance2]
        for i, tool_instance_mock in enumerate(tool_instances_mocks):
            langchain_tool = langchain_tools[i]
            assert isinstance(langchain_tool, ToolboxTool)
            assert langchain_tool.name == tool_instance_mock.__name__
            assert langchain_tool.description == tool_instance_mock.__doc__

            expected_args_schema = params_to_pydantic_model(
                tool_instance_mock._name, tool_instance_mock._params
            )
            assert_pydantic_models_equivalent(
                langchain_tool.args_schema,
                expected_args_schema,
                tool_instance_mock._name,
            )

        mock_core_load_toolset.assert_called_once_with(
            name=None, auth_token_getters={}, bound_params={}, strict=False
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    async def test_aload_tool(self, mock_sync_core_load_tool, toolbox_client):
        mock_core_sync_tool_instance = create_mock_core_sync_tool(
            name="test_async_loaded_tool",
            doc="Async loaded sync tool description.",
            model_name="AsyncTestToolModel",
        )
        mock_sync_core_load_tool.return_value = mock_core_sync_tool_instance

        langchain_tool = await toolbox_client.aload_tool("test_tool")

        assert isinstance(langchain_tool, ToolboxTool)
        assert langchain_tool.name == mock_core_sync_tool_instance.__name__
        assert langchain_tool.description == mock_core_sync_tool_instance.__doc__

        expected_args_schema = params_to_pydantic_model(
            mock_core_sync_tool_instance._name, mock_core_sync_tool_instance._params
        )
        assert_pydantic_models_equivalent(
            langchain_tool.args_schema,
            expected_args_schema,
            mock_core_sync_tool_instance._name,
        )

        mock_sync_core_load_tool.assert_called_once_with(
            name="test_tool", auth_token_getters={}, bound_params={}
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    async def test_aload_toolset(self, mock_sync_core_load_toolset, toolbox_client):
        mock_core_sync_tool1 = create_mock_core_sync_tool(
            name="async-tool-0", doc="async desc 0", model_name="AT0Model"
        )
        mock_core_sync_tool2 = create_mock_core_sync_tool(
            name="async-tool-1",
            doc="async desc 1",
            model_name="AT1Model",
            params=[CoreParameterSchema(name="p1", type="string", description="P1")],
        )

        mock_sync_core_load_toolset.return_value = [
            mock_core_sync_tool1,
            mock_core_sync_tool2,
        ]

        langchain_tools = await toolbox_client.aload_toolset()
        assert len(langchain_tools) == 2

        tool_instances_mocks = [mock_core_sync_tool1, mock_core_sync_tool2]
        for i, tool_instance_mock in enumerate(tool_instances_mocks):
            langchain_tool = langchain_tools[i]
            assert isinstance(langchain_tool, ToolboxTool)
            assert langchain_tool.name == tool_instance_mock.__name__

            expected_args_schema = params_to_pydantic_model(
                tool_instance_mock._name, tool_instance_mock._params
            )
            assert_pydantic_models_equivalent(
                langchain_tool.args_schema,
                expected_args_schema,
                tool_instance_mock._name,
            )

        mock_sync_core_load_toolset.assert_called_once_with(
            name=None, auth_token_getters={}, bound_params={}, strict=False
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    def test_load_tool_with_args(self, mock_core_load_tool, toolbox_client):
        mock_core_tool_instance = create_mock_core_sync_tool()
        mock_core_load_tool.return_value = mock_core_tool_instance

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}
        # Scenario 1: auth_token_getters takes precedence
        with pytest.warns(DeprecationWarning) as record:
            tool = toolbox_client.load_tool(
                "test_tool_name",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        assert len(record) == 2
        messages = sorted([str(r.message) for r in record])
        # Warning for auth_headers when auth_token_getters is also present
        assert (
            "Both `auth_token_getters` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_token_getters` will be used."
            in messages
        )
        # Warning for auth_tokens when auth_token_getters is also present
        assert (
            "Both `auth_token_getters` and `auth_tokens` are provided. `auth_tokens` is deprecated, and `auth_token_getters` will be used."
            in messages
        )

        assert isinstance(tool, ToolboxTool)
        mock_core_load_tool.assert_called_with(
            name="test_tool_name",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
        )
        mock_core_load_tool.reset_mock()

        # Scenario 2: auth_tokens and auth_headers provided, auth_token_getters is default (empty initially)
        with pytest.warns(DeprecationWarning) as record:
            toolbox_client.load_tool(
                "test_tool_name_2",
                auth_tokens=auth_tokens_deprecated,  # This will be used for auth_token_getters
                auth_headers=auth_headers_deprecated,  # This will warn as auth_token_getters is now populated
                bound_params=bound_params,
            )
        assert len(record) == 2
        messages = sorted([str(r.message) for r in record])

        assert (
            messages[0]
            == "Argument `auth_tokens` is deprecated. Use `auth_token_getters` instead."
        )
        assert (
            messages[1]
            == "Both `auth_token_getters` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_token_getters` will be used."
        )

        expected_getters_for_call = auth_tokens_deprecated

        mock_core_load_tool.assert_called_with(
            name="test_tool_name_2",
            auth_token_getters=expected_getters_for_call,
            bound_params=bound_params,
        )
        mock_core_load_tool.reset_mock()

        with pytest.warns(
            DeprecationWarning,
            match="Argument `auth_headers` is deprecated. Use `auth_token_getters` instead.",
        ) as record:
            toolbox_client.load_tool(
                "test_tool_name_3",
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        assert len(record) == 1

        mock_core_load_tool.assert_called_with(
            name="test_tool_name_3",
            auth_token_getters=auth_headers_deprecated,
            bound_params=bound_params,
        )

    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    def test_load_toolset_with_args(self, mock_core_load_toolset, toolbox_client):
        mock_core_tool_instance = create_mock_core_sync_tool(model_name="MySetModel")
        mock_core_load_toolset.return_value = [mock_core_tool_instance]

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}
        toolset_name = "my_toolset"

        with pytest.warns(DeprecationWarning) as record:
            tools = toolbox_client.load_toolset(
                toolset_name=toolset_name,
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
                strict=True,
            )
        assert len(record) == 2

        assert len(tools) == 1
        assert isinstance(tools[0], ToolboxTool)
        mock_core_load_toolset.assert_called_with(
            name=toolset_name,
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
            strict=True,
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_tool")
    async def test_aload_tool_with_args(self, mock_sync_core_load_tool, toolbox_client):
        mock_core_tool_instance = create_mock_core_sync_tool(
            model_name="MyAsyncToolModel"
        )
        mock_sync_core_load_tool.return_value = mock_core_tool_instance

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}

        with pytest.warns(DeprecationWarning) as record:
            tool = await toolbox_client.aload_tool(
                "test_tool",
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        assert len(record) == 2

        assert isinstance(tool, ToolboxTool)
        mock_sync_core_load_tool.assert_called_with(
            name="test_tool",
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    async def test_aload_toolset_with_args(
        self, mock_sync_core_load_toolset, toolbox_client
    ):
        mock_core_tool_instance = create_mock_core_sync_tool(
            model_name="MyAsyncSetModel"
        )
        mock_sync_core_load_toolset.return_value = [mock_core_tool_instance]

        auth_token_getters = {"token_getter1": lambda: "value1"}
        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}
        toolset_name = "my_async_toolset"

        with pytest.warns(DeprecationWarning) as record:
            tools = await toolbox_client.aload_toolset(
                toolset_name,
                auth_token_getters=auth_token_getters,
                auth_tokens=auth_tokens_deprecated,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
                strict=True,
            )
        assert len(record) == 2

        assert len(tools) == 1
        assert isinstance(tools[0], ToolboxTool)
        mock_sync_core_load_toolset.assert_called_with(
            name=toolset_name,
            auth_token_getters=auth_token_getters,
            bound_params=bound_params,
            strict=True,
        )

    @pytest.mark.asyncio
    @patch("toolbox_core.sync_client.ToolboxSyncClient.load_toolset")
    async def test_aload_toolset_with_deprecated_args(
        self, mock_sync_core_load_toolset, toolbox_client
    ):
        mock_core_tool_instance = create_mock_core_sync_tool(
            model_name="MyAsyncSetModel"
        )
        mock_sync_core_load_toolset.return_value = [mock_core_tool_instance]

        auth_tokens_deprecated = {"token_deprecated": lambda: "value_dep"}
        auth_headers_deprecated = {"header_deprecated": lambda: "value_head_dep"}
        bound_params = {"param1": "value4"}
        toolset_name = "my_async_toolset"

        # Scenario 2: auth_tokens and auth_headers provided, auth_token_getters is default (empty initially)
        with pytest.warns(DeprecationWarning) as record:
            await toolbox_client.aload_toolset(
                toolset_name,
                auth_tokens=auth_tokens_deprecated,  # This will be used for auth_token_getters
                auth_headers=auth_headers_deprecated,  # This will warn as auth_token_getters is now populated
                bound_params=bound_params,
            )
        assert len(record) == 2
        messages = sorted([str(r.message) for r in record])

        assert (
            messages[0]
            == "Argument `auth_tokens` is deprecated. Use `auth_token_getters` instead."
        )
        assert (
            messages[1]
            == "Both `auth_token_getters` and `auth_headers` are provided. `auth_headers` is deprecated, and `auth_token_getters` will be used."
        )

        expected_getters_for_call = auth_tokens_deprecated

        mock_sync_core_load_toolset.assert_called_with(
            name=toolset_name,
            auth_token_getters=expected_getters_for_call,
            bound_params=bound_params,
            strict=False,
        )
        mock_sync_core_load_toolset.reset_mock()

        with pytest.warns(
            DeprecationWarning,
            match="Argument `auth_headers` is deprecated. Use `auth_token_getters` instead.",
        ) as record:
            await toolbox_client.aload_toolset(
                toolset_name,
                auth_headers=auth_headers_deprecated,
                bound_params=bound_params,
            )
        assert len(record) == 1

        mock_sync_core_load_toolset.assert_called_with(
            name=toolset_name,
            auth_token_getters=auth_headers_deprecated,
            bound_params=bound_params,
            strict=False,
        )

    @patch("toolbox_langchain.client.ToolboxCoreSyncClient")
    def test_init_with_client_headers(self, mock_core_client_constructor):
        """Tests that client_headers are passed to the core client during initialization."""
        headers = {"X-Test-Header": "value"}
        ToolboxClient(URL, client_headers=headers)
        mock_core_client_constructor.assert_called_once_with(
            url=URL, client_headers=headers
        )

    @patch("toolbox_langchain.client.ToolboxCoreSyncClient")
    def test_context_manager(self, mock_core_client_constructor):
        """Tests that the client can be used as a context manager."""
        with ToolboxClient(URL) as client:
            assert isinstance(client, ToolboxClient)
            mock_core_client_constructor.return_value.close.assert_not_called()
        mock_core_client_constructor.return_value.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("toolbox_langchain.client.ToolboxCoreSyncClient")
    async def test_async_context_manager(self, mock_core_client_constructor):
        """Tests that the client can be used as an async context manager."""
        async with ToolboxClient(URL) as client:
            assert isinstance(client, ToolboxClient)
            mock_core_client_constructor.return_value.close.assert_not_called()
        mock_core_client_constructor.return_value.close.assert_called_once()

    @patch("toolbox_langchain.client.ToolboxCoreSyncClient")
    def test_close(self, mock_core_client_constructor):
        """Tests the close method."""
        client = ToolboxClient(URL)
        client.close()
        mock_core_client_constructor.return_value.close.assert_called_once()
