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

from unittest.mock import AsyncMock, patch
from warnings import catch_warnings, simplefilter

import pytest
from aiohttp import ClientSession
from toolbox_core.client import ToolboxClient as ToolboxCoreClient
from toolbox_core.protocol import ManifestSchema
from toolbox_core.protocol import ParameterSchema as CoreParameterSchema
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool
from toolbox_core.utils import params_to_pydantic_model

from toolbox_langchain.async_client import AsyncToolboxClient
from toolbox_langchain.async_tools import AsyncToolboxTool

URL = "http://test_url"
MANIFEST_JSON = {
    "serverVersion": "1.0.0",
    "tools": {
        "test_tool_1": {
            "description": "Test Tool 1 Description",
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "Param 1",
                }
            ],
        },
        "test_tool_2": {
            "description": "Test Tool 2 Description",
            "parameters": [
                {
                    "name": "param2",
                    "type": "integer",
                    "description": "Param 2",
                }
            ],
        },
    },
}


@pytest.mark.asyncio
class TestAsyncToolboxClient:
    @pytest.fixture()
    def manifest_schema(self):
        return ManifestSchema(**MANIFEST_JSON)

    @pytest.fixture()
    def mock_session(self):
        return AsyncMock(spec=ClientSession)

    @pytest.fixture
    def mock_core_client_instance(self, manifest_schema, mock_session):
        mock = AsyncMock(spec=ToolboxCoreClient)

        async def mock_load_tool_impl(name, auth_token_getters, bound_params):
            tool_schema_dict = MANIFEST_JSON["tools"].get(name)
            if not tool_schema_dict:
                raise ValueError(f"Tool '{name}' not in mock manifest_dict")

            core_params = [
                CoreParameterSchema(**p) for p in tool_schema_dict["parameters"]
            ]
            # Return a mock that looks like toolbox_core.tool.ToolboxTool
            core_tool_mock = AsyncMock(spec=ToolboxCoreTool)
            core_tool_mock.__name__ = name
            core_tool_mock.__doc__ = tool_schema_dict["description"]
            core_tool_mock._pydantic_model = params_to_pydantic_model(name, core_params)
            # Add other necessary attributes or method mocks if AsyncToolboxTool uses them
            return core_tool_mock

        mock.load_tool = AsyncMock(side_effect=mock_load_tool_impl)

        async def mock_load_toolset_impl(
            name, auth_token_getters, bound_params, strict
        ):
            core_tools_list = []
            for tool_name_iter, tool_schema_dict in MANIFEST_JSON["tools"].items():
                core_params = [
                    CoreParameterSchema(**p) for p in tool_schema_dict["parameters"]
                ]
                core_tool_mock = AsyncMock(spec=ToolboxCoreTool)
                core_tool_mock.__name__ = tool_name_iter
                core_tool_mock.__doc__ = tool_schema_dict["description"]
                core_tool_mock._pydantic_model = params_to_pydantic_model(
                    tool_name_iter, core_params
                )
                core_tools_list.append(core_tool_mock)
            return core_tools_list

        mock.load_toolset = AsyncMock(side_effect=mock_load_toolset_impl)
        # Mock the session attribute if it's directly accessed by AsyncToolboxClient tests
        mock._ToolboxClient__session = mock_session
        return mock

    @pytest.fixture()
    def mock_client(self, mock_session, mock_core_client_instance):
        # Patch the ToolboxCoreClient constructor used by AsyncToolboxClient
        with patch(
            "toolbox_langchain.async_client.ToolboxCoreClient",
            return_value=mock_core_client_instance,
        ):
            client = AsyncToolboxClient(URL, session=mock_session)
            # Ensure the mocked core client is used
            client._AsyncToolboxClient__core_client = mock_core_client_instance
            return client

    async def test_create_with_existing_session(self, mock_client, mock_session):
        # AsyncToolboxClient stores the core_client, which stores the session
        assert (
            mock_client._AsyncToolboxClient__core_client._ToolboxClient__session
            == mock_session
        )

    async def test_aload_tool(
        self,
        mock_client,
        manifest_schema,  # mock_session removed as it's part of mock_core_client_instance
    ):
        tool_name = "test_tool_1"
        # manifest_schema is used by mock_core_client_instance fixture to provide tool details

        tool = await mock_client.aload_tool(tool_name)

        # Assert that the core client's load_tool was called correctly
        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name, auth_token_getters={}, bound_params={}
        )
        assert isinstance(tool, AsyncToolboxTool)
        assert (
            tool.name == tool_name
        )  # AsyncToolboxTool gets its name from the core_tool

    async def test_aload_tool_auth_headers_deprecated(
        self, mock_client, manifest_schema
    ):
        tool_name = "test_tool_1"
        auth_lambda = lambda: "Bearer token"  # Define lambda once
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_headers={"Authorization": auth_lambda},  # Use the defined lambda
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name,
            auth_token_getters={"Authorization": auth_lambda},
            bound_params={},
        )

    async def test_aload_tool_auth_headers_and_tokens(
        self, mock_client, manifest_schema
    ):
        tool_name = "test_tool_1"
        auth_getters = {"test": lambda: "token"}
        auth_headers_lambda = lambda: "Bearer token"  # Define lambda once

        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_headers={
                    "Authorization": auth_headers_lambda
                },  # Use defined lambda
                auth_token_getters=auth_getters,
            )
            assert (
                len(w) == 1
            )  # Only one warning because auth_token_getters takes precedence
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)  # Warning for auth_headers

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name, auth_token_getters=auth_getters, bound_params={}
        )

    async def test_aload_toolset(
        self, mock_client, manifest_schema  # mock_session removed
    ):
        tools = await mock_client.aload_toolset()

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None, auth_token_getters={}, bound_params={}, strict=False
        )
        assert len(tools) == 2  # Based on MANIFEST_JSON
        for tool in tools:
            assert isinstance(tool, AsyncToolboxTool)
            assert tool.name in ["test_tool_1", "test_tool_2"]

    async def test_aload_toolset_with_toolset_name(
        self, mock_client, manifest_schema  # mock_session removed
    ):
        toolset_name = "test_toolset_1"  # This name isn't in MANIFEST_JSON, but load_toolset mock doesn't filter by it
        tools = await mock_client.aload_toolset(toolset_name=toolset_name)

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=toolset_name, auth_token_getters={}, bound_params={}, strict=False
        )
        assert len(tools) == 2
        for tool in tools:
            assert isinstance(tool, AsyncToolboxTool)
            assert tool.name in ["test_tool_1", "test_tool_2"]

    async def test_aload_toolset_auth_headers_deprecated(
        self, mock_client, manifest_schema
    ):
        auth_lambda = lambda: "Bearer token"  # Define lambda once
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(
                auth_headers={"Authorization": auth_lambda}  # Use defined lambda
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None,
            auth_token_getters={"Authorization": auth_lambda},
            bound_params={},
            strict=False,
        )

    async def test_aload_toolset_auth_headers_and_tokens(
        self, mock_client, manifest_schema
    ):
        auth_getters = {"test": lambda: "token"}
        auth_headers_lambda = lambda: "Bearer token"  # Define lambda once
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(
                auth_headers={
                    "Authorization": auth_headers_lambda
                },  # Use defined lambda
                auth_token_getters=auth_getters,
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None, auth_token_getters=auth_getters, bound_params={}, strict=False
        )

    async def test_load_tool_not_implemented(self, mock_client):
        with pytest.raises(NotImplementedError) as excinfo:
            mock_client.load_tool("test_tool")
        assert "Synchronous methods not supported by async client." in str(
            excinfo.value
        )

    async def test_load_toolset_not_implemented(self, mock_client):
        with pytest.raises(NotImplementedError) as excinfo:
            mock_client.load_toolset()
        assert "Synchronous methods not supported by async client." in str(
            excinfo.value
        )
