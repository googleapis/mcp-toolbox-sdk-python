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
from toolbox_core.protocol import ParameterSchema as CoreParameterSchema
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool

from toolbox_llamaindex.async_client import AsyncToolboxClient
from toolbox_llamaindex.async_tools import AsyncToolboxTool

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
    def mock_session(self):
        return AsyncMock(spec=ClientSession)

    @pytest.fixture
    def mock_core_client_instance(self, mock_session):
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
            core_tool_mock._name = name
            core_tool_mock._params = core_params
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
                core_tool_mock._name = tool_name_iter
                core_tool_mock._params = core_params
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
            "toolbox_llamaindex.async_client.ToolboxCoreClient",
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
    ):
        tool_name = "test_tool_1"
        test_bound_params = {"bp1": "value1"}

        tool = await mock_client.aload_tool(tool_name, bound_params=test_bound_params)

        # Assert that the core client's load_tool was called correctly
        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name, auth_token_getters={}, bound_params=test_bound_params
        )
        assert isinstance(tool, AsyncToolboxTool)
        assert (
            tool.metadata.name == tool_name
        )  # AsyncToolboxTool gets its name from the core_tool

    async def test_aload_tool_auth_headers_deprecated(self, mock_client):
        tool_name = "test_tool_1"
        auth_lambda = lambda: "Bearer token"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_headers={"Authorization": auth_lambda},
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
            assert "Use `auth_token_getters` instead" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name,
            auth_token_getters={"Authorization": auth_lambda},
            bound_params={},
        )

    async def test_aload_tool_auth_headers_and_getters_precedence(self, mock_client):
        tool_name = "test_tool_1"
        auth_getters = {"test_source": lambda: "id_token_from_getters"}
        auth_headers_lambda = lambda: "Bearer token_from_headers"

        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_headers={"Authorization": auth_headers_lambda},
                auth_token_getters=auth_getters,
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
            assert "`auth_token_getters` will be used" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name, auth_token_getters=auth_getters, bound_params={}
        )

    async def test_aload_tool_auth_tokens_deprecated(self, mock_client):
        tool_name = "test_tool_1"
        token_lambda = lambda: "id_token"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_tokens={"some_token_key": token_lambda},
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_tokens" in str(w[-1].message)
            assert "Use `auth_token_getters` instead" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name,
            auth_token_getters={"some_token_key": token_lambda},
            bound_params={},
        )

    async def test_aload_tool_auth_tokens_and_getters_precedence(self, mock_client):
        tool_name = "test_tool_1"
        auth_getters = {"real_source": lambda: "token_from_getters"}
        token_lambda = lambda: "token_from_auth_tokens"

        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_tool(
                tool_name,
                auth_tokens={"deprecated_source": token_lambda},
                auth_token_getters=auth_getters,
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_tokens" in str(w[-1].message)
            assert "`auth_token_getters` will be used" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_tool.assert_called_once_with(
            name=tool_name, auth_token_getters=auth_getters, bound_params={}
        )

    async def test_aload_toolset(self, mock_client):
        test_bound_params = {"bp_set": "value_set"}
        tools = await mock_client.aload_toolset(
            bound_params=test_bound_params, strict=True
        )

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None,
            auth_token_getters={},
            bound_params=test_bound_params,
            strict=True,
        )
        assert len(tools) == 2
        for tool in tools:
            assert isinstance(tool, AsyncToolboxTool)
            assert tool.metadata.name in ["test_tool_1", "test_tool_2"]

    async def test_aload_toolset_with_toolset_name(self, mock_client):
        toolset_name = "test_toolset_1"
        tools = await mock_client.aload_toolset(toolset_name=toolset_name)

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=toolset_name, auth_token_getters={}, bound_params={}, strict=False
        )
        assert len(tools) == 2
        for tool in tools:
            assert isinstance(tool, AsyncToolboxTool)

    async def test_aload_toolset_auth_headers_deprecated(self, mock_client):
        auth_lambda = lambda: "Bearer token"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(auth_headers={"Authorization": auth_lambda})
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
            assert "Use `auth_token_getters` instead" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None,
            auth_token_getters={"Authorization": auth_lambda},
            bound_params={},
            strict=False,
        )

    async def test_aload_toolset_auth_headers_and_getters_precedence(  # Renamed for clarity
        self, mock_client
    ):
        auth_getters = {"test_source": lambda: "id_token_from_getters"}
        auth_headers_lambda = lambda: "Bearer token_from_headers"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(
                auth_headers={"Authorization": auth_headers_lambda},
                auth_token_getters=auth_getters,
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_headers" in str(w[-1].message)
            assert "`auth_token_getters` will be used" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None,
            auth_token_getters=auth_getters,
            bound_params={},
            strict=False,  # auth_getters takes precedence
        )

    async def test_aload_toolset_auth_tokens_deprecated(self, mock_client):
        token_lambda = lambda: "id_token"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(
                auth_tokens={"some_token_key": token_lambda}
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_tokens" in str(w[-1].message)
            assert "Use `auth_token_getters` instead" in str(w[-1].message)

        mock_client._AsyncToolboxClient__core_client.load_toolset.assert_called_once_with(
            name=None,
            auth_token_getters={"some_token_key": token_lambda},
            bound_params={},
            strict=False,
        )

    async def test_aload_toolset_auth_tokens_and_getters_precedence(self, mock_client):
        auth_getters = {"real_source": lambda: "token_from_getters"}
        token_lambda = lambda: "token_from_auth_tokens"
        with catch_warnings(record=True) as w:
            simplefilter("always")
            await mock_client.aload_toolset(
                auth_tokens={"deprecated_source": token_lambda},
                auth_token_getters=auth_getters,
            )
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "auth_tokens" in str(w[-1].message)
            assert "`auth_token_getters` will be used" in str(w[-1].message)

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

    @patch("toolbox_llamaindex.async_client.ToolboxCoreClient")
    async def test_init_with_client_headers(
        self, mock_core_client_constructor, mock_session
    ):
        """Tests that client_headers are passed to the core client during initialization."""
        headers = {"X-Test-Header": "value"}
        AsyncToolboxClient(URL, session=mock_session, client_headers=headers)
        mock_core_client_constructor.assert_called_once_with(
            url=URL, session=mock_session, client_headers=headers
        )
