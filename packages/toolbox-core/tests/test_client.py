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


import inspect
from typing import Mapping, Optional
from unittest.mock import AsyncMock
from typing import Mapping, Optional
from unittest.mock import AsyncMock

import pytest

from toolbox_core.client import ToolboxClient
from toolbox_core.itransport import ITransport
from toolbox_core.client import ToolboxClient
from toolbox_core.itransport import ITransport
from toolbox_core.protocol import ManifestSchema, ParameterSchema, ToolSchema

TEST_BASE_URL = "http://toolbox.example.com"


class MockTransport(ITransport):
    """A mock transport for testing the ToolboxClient."""

    def __init__(self, base_url: str):
        self._base_url = base_url
        self.tool_get_mock = AsyncMock()
        self.tools_list_mock = AsyncMock()
        self.tool_invoke_mock = AsyncMock()
        self.close_mock = AsyncMock()

    @property
    def base_url(self) -> str:
        return self._base_url

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        return await self.tool_get_mock(tool_name, headers)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        return await self.tools_list_mock(toolset_name, headers)

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        return await self.tool_invoke_mock(tool_name, arguments, headers)

    async def close(self):
        await self.close_mock()


@pytest.fixture
def mock_transport() -> MockTransport:
    """Provides a mock transport instance."""
    return MockTransport(TEST_BASE_URL)


class MockTransport(ITransport):
    """A mock transport for testing the ToolboxClient."""

    def __init__(self, base_url: str):
        self._base_url = base_url
        self.tool_get_mock = AsyncMock()
        self.tools_list_mock = AsyncMock()
        self.tool_invoke_mock = AsyncMock()
        self.close_mock = AsyncMock()

    @property
    def base_url(self) -> str:
        return self._base_url

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        return await self.tool_get_mock(tool_name, headers)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        return await self.tools_list_mock(toolset_name, headers)

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        return await self.tool_invoke_mock(tool_name, arguments, headers)

    async def close(self):
        await self.close_mock()


@pytest.fixture
def mock_transport() -> MockTransport:
    """Provides a mock transport instance."""
    return MockTransport(TEST_BASE_URL)


@pytest.fixture()
def test_tool_str():
    return ToolSchema(
        description="Test Tool with String input",
        parameters=[
            ParameterSchema(
                name="param1", type="string", description="Description of Param1"
            )
        ],
    )


@pytest.fixture()
def test_tool_int_bool():
    return ToolSchema(
        description="Test Tool with Int, Bool",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(name="argB", type="boolean", description="Argument B"),
        ],
    )


@pytest.fixture()
def test_tool_auth():
    return ToolSchema(
        description="Test Tool with Int,Bool+Auth",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(
                name="argB",
                type="boolean",
                description="Argument B",
                authSources=["my-auth-service"],
            ),
        ],
    )


@pytest.fixture
def tool_schema_minimal():
    """A tool with no parameters, no auth."""
    return ToolSchema(
        description="Minimal Test Tool",
        parameters=[],
    )


@pytest.fixture
def tool_schema_requires_auth_X():
    """A tool requiring 'auth_service_X'."""
    return ToolSchema(
        description="Tool Requiring Auth X",
        parameters=[
            ParameterSchema(
                name="auth_param_X",
                name="auth_param_X",
                type="string",
                description="Auth X Token",
                authSources=["auth_service_X"],
            ),
            ParameterSchema(name="data", type="string", description="Some data"),
        ],
    )


@pytest.fixture
def tool_schema_with_param_P():
    """A tool with a specific parameter 'param_P'."""
    return ToolSchema(
        description="Tool with Parameter P",
        parameters=[
            ParameterSchema(name="param_P", type="string", description="Parameter P"),
        ],
    )


@pytest.mark.asyncio
async def test_load_tool_success(mock_transport, test_tool_str):
async def test_load_tool_success(mock_transport, test_tool_str):
    """
    Tests successfully loading a tool when the transport returns a valid manifest.
    Tests successfully loading a tool when the transport returns a valid manifest.
    """
    TOOL_NAME = "test_tool_1"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str}
    )
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.return_value = "ok"

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        client._ToolboxClient__transport = mock_transport
        loaded_tool = await client.load_tool(TOOL_NAME)

        assert callable(loaded_tool)
        assert loaded_tool.__name__ == TOOL_NAME
        expected_description = (
            test_tool_str.description
            + "\n\nArgs:\n    param1 (str): Description of Param1"
            + "\n\nArgs:\n    param1 (str): Description of Param1"
        )
        assert loaded_tool.__doc__ == expected_description

        sig = inspect.signature(loaded_tool)
        assert list(sig.parameters.keys()) == [p.name for p in test_tool_str.parameters]

        assert await loaded_tool("some value") == "ok"
        mock_transport.tool_get_mock.assert_awaited_once_with(TOOL_NAME, {})
        mock_transport.tool_invoke_mock.assert_awaited_once_with(
            TOOL_NAME, {"param1": "some value"}, {}
        )
        mock_transport.tool_get_mock.assert_awaited_once_with(TOOL_NAME, {})
        mock_transport.tool_invoke_mock.assert_awaited_once_with(
            TOOL_NAME, {"param1": "some value"}, {}
        )


@pytest.mark.asyncio
async def test_load_toolset_success(
    mock_transport, test_tool_str, test_tool_int_bool
):
    """Tests successfully loading a toolset with multiple tools."""
    TOOLSET_NAME = "my_toolset"
    TOOL1 = "tool1"
    TOOL2 = "tool2"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL1: test_tool_str, TOOL2: test_tool_int_bool}
    )
    mock_transport.tools_list_mock.return_value = manifest
    mock_transport.tools_list_mock.return_value = manifest

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        client._ToolboxClient__transport = mock_transport
        tools = await client.load_toolset(TOOLSET_NAME)

        assert isinstance(tools, list)
        assert len(tools) == len(manifest.tools)
        assert {t.__name__ for t in tools} == manifest.tools.keys()
        mock_transport.tools_list_mock.assert_awaited_once_with(TOOLSET_NAME, {})
        mock_transport.tools_list_mock.assert_awaited_once_with(TOOLSET_NAME, {})


@pytest.mark.asyncio
async def test_invoke_tool_server_error(mock_transport, test_tool_str):
    """Tests that invoking a tool raises an Exception when the transport raises an error."""
async def test_invoke_tool_server_error(mock_transport, test_tool_str):
    """Tests that invoking a tool raises an Exception when the transport raises an error."""
    TOOL_NAME = "server_error_tool"
    ERROR_MESSAGE = "Simulated Server Error"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str}
    )
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.side_effect = Exception(ERROR_MESSAGE)

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        client._ToolboxClient__transport = mock_transport
        loaded_tool = await client.load_tool(TOOL_NAME)

        with pytest.raises(Exception, match=ERROR_MESSAGE):
            await loaded_tool(param1="some input")


@pytest.mark.asyncio
async def test_load_tool_not_found_in_manifest(mock_transport, test_tool_str):
async def test_load_tool_not_found_in_manifest(mock_transport, test_tool_str):
    """
    Tests that load_tool raises an Exception when the requested tool name is not
    found in the manifest returned by the server.
    found in the manifest returned by the server.
    """
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_xyz"
    mismatched_manifest = ManifestSchema(
    mismatched_manifest = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str}
    )
    mock_transport.tool_get_mock.return_value = mismatched_manifest
    )
    mock_transport.tool_get_mock.return_value = mismatched_manifest

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        client._ToolboxClient__transport = mock_transport
        with pytest.raises(
            ValueError, match=f"Tool '{REQUESTED_TOOL_NAME}' not found!"
        ):
            await client.load_tool(REQUESTED_TOOL_NAME)

    mock_transport.tool_get_mock.assert_awaited_once_with(REQUESTED_TOOL_NAME, {})
    mock_transport.tool_get_mock.assert_awaited_once_with(REQUESTED_TOOL_NAME, {})


class TestAuth:
    @pytest.fixture
    def expected_header(self):
        return "some_token_for_testing"

    @pytest.fixture
    def tool_name(self):
        return "tool1"

    @pytest.fixture
    def mock_transport_auth(self, test_tool_auth, tool_name, expected_header):
        transport = MockTransport(TEST_BASE_URL)
    @pytest.fixture
    def mock_transport_auth(self, test_tool_auth, tool_name, expected_header):
        transport = MockTransport(TEST_BASE_URL)
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_auth}
        )
        transport.tool_get_mock.return_value = manifest

        async def invoke_checker(t_name, args, headers):
            assert headers.get("my-auth-service_token") == expected_header
            return "{}"

        transport.tool_invoke_mock.side_effect = invoke_checker
        return transport
        transport.tool_get_mock.return_value = manifest

        async def invoke_checker(t_name, args, headers):
            assert headers.get("my-auth-service_token") == expected_header
            return "{}"

        transport.tool_invoke_mock.side_effect = invoke_checker
        return transport

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_success(
        self, tool_name, expected_header, mock_transport_auth
        self, tool_name, expected_header, mock_transport_auth
    ):
        """Tests 'load_tool' with auth token is specified."""

        def token_handler():
            return expected_header

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(
                tool_name, auth_token_getters={"my-auth-service": token_handler}
            )
            await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_awaited_once()
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(
                tool_name, auth_token_getters={"my-auth-service": token_handler}
            )
            await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_with_add_token_success(
        self, tool_name, expected_header, mock_transport_auth
        self, tool_name, expected_header, mock_transport_auth
    ):
        """Tests 'add_auth_token_getters' with auth token is specified."""
        """Tests 'add_auth_token_getters' with auth token is specified."""

        def token_handler():
            return expected_header

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
            await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_awaited_once()
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
            await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_fail_no_token(self, tool_name, mock_transport_auth):
        """Tests 'load_tool' without required auth token fails."""
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            with pytest.raises(Exception):
                await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_auth_token_getters_duplicate_fail(
        self, tool_name, mock_transport_auth
    ):
    async def test_add_auth_token_getters_duplicate_fail(
        self, tool_name, mock_transport_auth
    ):
        """
        Tests that adding a duplicate auth token getter raises ValueError.
        """
        AUTH_SERVICE = "my-auth-service"
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            authed_tool = tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token1"})
            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` already registered in tool `{tool_name}`.",
            ):
                authed_tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token2"})
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            authed_tool = tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token1"})
            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` already registered in tool `{tool_name}`.",
            ):
                authed_tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token2"})

    @pytest.mark.asyncio
    async def test_add_auth_token_getters_missing_fail(
        self, tool_name, mock_transport_auth
    ):
    async def test_add_auth_token_getters_missing_fail(
        self, tool_name, mock_transport_auth
    ):
        """
        Tests that adding a missing auth token getter raises ValueError.
        """
        AUTH_SERVICE = "xmy-auth-service"
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` unused by tool `{tool_name}`.",
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` unused by tool `{tool_name}`.",
            ):
                tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token"})
                tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token"})

    @pytest.mark.asyncio
    async def test_constructor_getters_missing_fail(
        self, tool_name, mock_transport_auth
    async def test_constructor_getters_missing_fail(
        self, tool_name, mock_transport_auth
    ):
        """
        Tests that providing a missing auth token getter in constructor raises ValueError.
        Tests that providing a missing auth token getter in constructor raises ValueError.
        """
        AUTH_SERVICE = "xmy-auth-service"
        AUTH_SERVICE = "xmy-auth-service"
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            client._ToolboxClient__transport = mock_transport_auth
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{tool_name}': unused auth tokens: {AUTH_SERVICE}.",
                match=f"Validation failed for tool '{tool_name}': unused auth tokens: {AUTH_SERVICE}.",
            ):
                await client.load_tool(
                    tool_name, auth_token_getters={AUTH_SERVICE: lambda: "token"}
                )