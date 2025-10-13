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
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

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
    """
    Tests successfully loading a tool when the transport returns a valid manifest.
    """
    TOOL_NAME = "test_tool_1"
    manifest = ManifestSchema(serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str})
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.return_value = "ok"

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        loaded_tool = await client.load_tool(TOOL_NAME)

        assert callable(loaded_tool)
        assert loaded_tool.__name__ == TOOL_NAME
        expected_description = (
            test_tool_str.description
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


@pytest.mark.asyncio
async def test_load_toolset_success(mock_transport, test_tool_str, test_tool_int_bool):
    """Tests successfully loading a toolset with multiple tools."""
    TOOLSET_NAME = "my_toolset"
    TOOL1 = "tool1"
    TOOL2 = "tool2"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL1: test_tool_str, TOOL2: test_tool_int_bool}
    )
    mock_transport.tools_list_mock.return_value = manifest

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        tools = await client.load_toolset(TOOLSET_NAME)

        assert isinstance(tools, list)
        assert len(tools) == len(manifest.tools)
        assert {t.__name__ for t in tools} == manifest.tools.keys()
        mock_transport.tools_list_mock.assert_awaited_once_with(TOOLSET_NAME, {})


@pytest.mark.asyncio
async def test_invoke_tool_server_error(mock_transport, test_tool_str):
    """Tests that invoking a tool raises an Exception when the transport raises an error."""
    TOOL_NAME = "server_error_tool"
    ERROR_MESSAGE = "Simulated Server Error"
    manifest = ManifestSchema(serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str})
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.side_effect = Exception(ERROR_MESSAGE)

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        loaded_tool = await client.load_tool(TOOL_NAME)

        with pytest.raises(Exception, match=ERROR_MESSAGE):
            await loaded_tool(param1="some input")


@pytest.mark.asyncio
async def test_load_tool_not_found_in_manifest(mock_transport, test_tool_str):
    """
    Tests that load_tool raises an Exception when the requested tool name is not
    found in the manifest returned by the server.
    """
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_xyz"
    mismatched_manifest = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str}
    )
    mock_transport.tool_get_mock.return_value = mismatched_manifest

    async with ToolboxClient(TEST_BASE_URL) as client:
        client._ToolboxClient__transport = mock_transport
        with pytest.raises(
            ValueError, match=f"Tool '{REQUESTED_TOOL_NAME}' not found!"
        ):
            await client.load_tool(REQUESTED_TOOL_NAME)

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
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_auth}
        )
        transport.tool_get_mock.return_value = manifest

        async def invoke_checker(t_name, args, headers):
            assert headers.get("my-auth-service_token") == expected_header
            return "{}"

        transport.tool_invoke_mock.side_effect = invoke_checker
        return transport

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_success(
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

    @pytest.mark.asyncio
    async def test_auth_with_add_token_success(
        self, tool_name, expected_header, mock_transport_auth
    ):
        """Tests 'add_auth_token_getters' with auth token is specified."""

        def token_handler():
            return expected_header

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            tool = await client.load_tool(tool_name)
            tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
            await tool(5)
            mock_transport_auth.tool_invoke_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_fail_no_token(
        self, tool_name, mock_transport_auth
    ):
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

    @pytest.mark.asyncio
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
            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` unused by tool `{tool_name}`.",
            ):
                tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token"})

    @pytest.mark.asyncio
    async def test_constructor_getters_missing_fail(
        self, tool_name, mock_transport_auth
    ):
        """
        Tests that providing a missing auth token getter in constructor raises ValueError.
        """
        AUTH_SERVICE = "xmy-auth-service"
        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport_auth
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{tool_name}': unused auth tokens: {AUTH_SERVICE}.",
            ):
                await client.load_tool(
                    tool_name, auth_token_getters={AUTH_SERVICE: lambda: "token"}
                )


class TestValidation:
    """Tests related to the bound_params and auth token validation functionality."""

    @pytest.mark.asyncio
    async def test_load_tool_with_bound_param_success(
        self, mock_transport, tool_schema_with_param_P
    ):
        """Tests loading a tool with a successfully bound parameter."""
        TOOL_NAME = "tool_with_p"
        BOUND_VALUE = "this_is_bound"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={TOOL_NAME: tool_schema_with_param_P}
        )
        mock_transport.tool_get_mock.return_value = manifest

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            tool = await client.load_tool(
                TOOL_NAME, bound_params={"param_P": BOUND_VALUE}
            )

            # The bound parameter should no longer be in the signature
            assert "param_P" not in inspect.signature(tool).parameters
            # Invoking the tool should not require the bound parameter
            await tool()
            mock_transport.tool_invoke_mock.assert_awaited_once_with(
                TOOL_NAME, {"param_P": BOUND_VALUE}, {}
            )

    @pytest.mark.asyncio
    async def test_load_tool_with_unused_bound_param_fail(
        self, mock_transport, tool_schema_minimal
    ):
        """Tests that load_tool fails if a bound_param is unused."""
        TOOL_NAME = "minimal_tool"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={TOOL_NAME: tool_schema_minimal}
        )
        mock_transport.tool_get_mock.return_value = manifest

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{TOOL_NAME}': unused bound parameters: unused_param.",
            ):
                await client.load_tool(
                    TOOL_NAME, bound_params={"unused_param": "some_value"}
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_with_partially_used_bound_param_fail(
        self, mock_transport, tool_schema_with_param_P, tool_schema_minimal
    ):
        """Tests that load_toolset fails in strict mode if a bound_param is only used by some tools."""
        TOOL_P = "tool_with_p"
        TOOL_MIN = "minimal_tool"
        manifest = ManifestSchema(
            serverVersion="0.0.0",
            tools={TOOL_P: tool_schema_with_param_P, TOOL_MIN: tool_schema_minimal},
        )
        mock_transport.tools_list_mock.return_value = manifest

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{TOOL_MIN}': unused bound parameters: param_P.",
            ):
                await client.load_toolset(
                    bound_params={"param_P": "some_value"}, strict=True
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_with_unused_bound_param_fail(
        self, mock_transport, tool_schema_minimal
    ):
        """Tests that load_toolset fails in non-strict mode if a bound_param is used by no tools."""
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={"tool1": tool_schema_minimal}
        )
        mock_transport.tools_list_mock.return_value = manifest
        TOOLSET_NAME = "my_set"

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            with pytest.raises(
                ValueError,
                match=f"Validation failed for toolset '{TOOLSET_NAME}': unused bound parameters could not be applied to any tool: param_Z.",
            ):
                await client.load_toolset(
                    TOOLSET_NAME, bound_params={"param_Z": "some_value"}
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_with_partially_used_auth_fail(
        self, mock_transport, tool_schema_requires_auth_X, tool_schema_minimal
    ):
        """Tests that load_toolset fails in strict mode if an auth token is only used by some tools."""
        TOOL_AUTH = "tool_with_auth"
        TOOL_MIN = "minimal_tool"
        manifest = ManifestSchema(
            serverVersion="0.0.0",
            tools={
                TOOL_AUTH: tool_schema_requires_auth_X,
                TOOL_MIN: tool_schema_minimal,
            },
        )
        mock_transport.tools_list_mock.return_value = manifest

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{TOOL_MIN}': unused auth tokens: auth_service_X.",
            ):
                await client.load_toolset(
                    auth_token_getters={"auth_service_X": lambda: "token"}, strict=True
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_with_unused_auth_fail(
        self, mock_transport, tool_schema_minimal
    ):
        """Tests that load_toolset fails in non-strict mode if an auth token is used by no tools."""
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={"tool1": tool_schema_minimal}
        )
        mock_transport.tools_list_mock.return_value = manifest
        TOOLSET_NAME = "my_set"

        async with ToolboxClient(TEST_BASE_URL) as client:
            client._ToolboxClient__transport = mock_transport
            with pytest.raises(
                ValueError,
                match=f"Validation failed for toolset '{TOOLSET_NAME}': unused auth tokens could not be applied to any tool: auth_service_Z.",
            ):
                await client.load_toolset(
                    TOOLSET_NAME,
                    auth_token_getters={"auth_service_Z": lambda: "token"},
                )


@pytest.fixture
def static_header() -> dict[str, str]:
    return {"X-Static-Header": "static-value"}


@pytest.fixture
def sync_callable_header_value() -> str:
    return "sync-callable-value"


@pytest.fixture
def sync_callable_header(sync_callable_header_value) -> dict[str, Mock]:
    return {"X-Sync-Callable-Header": Mock(return_value=sync_callable_header_value)}


@pytest.fixture
def async_callable_header_value() -> str:
    return "async-callable-value"


@pytest.fixture
def async_callable_header(async_callable_header_value) -> dict[str, AsyncMock]:
    return {
        "X-Async-Callable-Header": AsyncMock(return_value=async_callable_header_value)
    }


class TestClientHeaders:
    """Tests related to client headers."""

    def create_callback_factory(self, expected_header, callback_payload):
        async def callback(request, *args, **kwargs):
            for key, value in expected_header.items():
                assert request.headers[key] == value
            return web.json_response(callback_payload)

        return callback

    @pytest.mark.asyncio
    async def test_add_headers_success(self, mock_transport, tool_schema_minimal):
        """Tests that headers added via the deprecated add_headers are sent."""
        TOOL_NAME = "some_tool"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={TOOL_NAME: tool_schema_minimal}
        )
        mock_transport.tool_get_mock.return_value = manifest

        with pytest.warns(DeprecationWarning):
            client = ToolboxClient(TEST_BASE_URL)
            client._ToolboxClient__transport = mock_transport
            client.add_headers({"X-Test-Header": "TestValue"})

        await client.load_tool(TOOL_NAME)
        mock_transport.tool_get_mock.assert_awaited_once_with(
            TOOL_NAME, {"X-Test-Header": "TestValue"}
        )
        await client.close()

    @pytest.mark.asyncio
    async def test_load_tool_with_sync_callable_headers(
        self,
        mock_transport,
        test_tool_str,
        sync_callable_header,
        sync_callable_header_value,
    ):
        """Tests loading and invoking a tool with sync callable client
        headers."""
        tool_name = "tool_with_sync_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_sync"}
        header_key = list(sync_callable_header.keys())[0]
        header_mock = sync_callable_header[header_key]
        resolved_header = {header_key: sync_callable_header_value}

        mock_transport.tool_get_mock.return_value = manifest
        mock_transport.tool_invoke_mock.return_value = expected_payload["result"]

        async with ToolboxClient(
            TEST_BASE_URL, client_headers=sync_callable_header
        ) as client:
            client._ToolboxClient__transport = mock_transport
            tool = await client.load_tool(tool_name)
            header_mock.assert_called_once()  # GET

            header_mock.reset_mock()  # Reset before invoke

            result = await tool(param1="test")
            assert result == expected_payload["result"]
            header_mock.assert_called_once()  # POST/invoke
            mock_transport.tool_get_mock.assert_awaited_once_with(
                tool_name, resolved_header
            )
            mock_transport.tool_invoke_mock.assert_awaited_once_with(
                tool_name, {"param1": "test"}, resolved_header
            )

    @pytest.mark.asyncio
    async def test_load_tool_with_async_callable_headers(
        self,
        mock_transport,
        test_tool_str,
        async_callable_header,
        async_callable_header_value,
    ):
        """Tests loading and invoking a tool with async callable client
        headers."""
        tool_name = "tool_with_async_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_async"}

        header_key = list(async_callable_header.keys())[0]
        header_mock: AsyncMock = async_callable_header[header_key]  # Get the AsyncMock

        # Calculate expected result using the VALUE fixture
        resolved_header = {header_key: async_callable_header_value}

        mock_transport.tool_get_mock.return_value = manifest
        mock_transport.tool_invoke_mock.return_value = expected_payload["result"]

        async with ToolboxClient(
            TEST_BASE_URL, client_headers=async_callable_header
        ) as client:
            client._ToolboxClient__transport = mock_transport
            tool = await client.load_tool(tool_name)
            header_mock.assert_awaited_once()  # GET

            header_mock.reset_mock()

            result = await tool(param1="test")
            assert result == expected_payload["result"]
            header_mock.assert_awaited_once()  # POST/invoke
            mock_transport.tool_get_mock.assert_awaited_once_with(
                tool_name, resolved_header
            )
            mock_transport.tool_invoke_mock.assert_awaited_once_with(
                tool_name, {"param1": "test"}, resolved_header
            )

    @pytest.mark.asyncio
    async def test_load_toolset_with_headers(
        self, mock_transport, test_tool_str, static_header
    ):
        """Tests loading a toolset with client headers."""
        toolset_name = "toolset_with_headers"
        tool_name = "tool_in_set"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        mock_transport.tools_list_mock.return_value = manifest

        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            client._ToolboxClient__transport = mock_transport
            tools = await client.load_toolset(toolset_name)
            assert len(tools) == 1
            assert tools[0].__name__ == tool_name
            mock_transport.tools_list_mock.assert_awaited_once_with(
                toolset_name, static_header
            )

    @pytest.mark.asyncio
    async def test_add_headers_deprecation_warning(self):
        """Tests that add_headers issues a DeprecationWarning."""
        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.warns(
                DeprecationWarning,
                match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
            ):
                client.add_headers({"X-Deprecated-Test": "value"})

    @pytest.mark.asyncio
    async def test_add_headers_duplicate_fail(self, static_header):
        """Tests that adding a duplicate header via add_headers raises
        ValueError."""
        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            with pytest.warns(
                DeprecationWarning,
                match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
            ):
                with pytest.raises(
                    ValueError,
                    match=f"Client header\\(s\\) `X-Static-Header` already registered",
                ):
                    client.add_headers(static_header)
