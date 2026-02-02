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

from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from toolbox_core.mcp_transport.v20250618 import types
from toolbox_core.mcp_transport.v20250618.mcp import McpHttpTransportV20250618
from toolbox_core.protocol import ManifestSchema, Protocol


def create_fake_tools_list_result():
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="get_weather",
                description="Gets the weather.",
                inputSchema={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            )
        ]
    )


@pytest_asyncio.fixture
async def transport():
    mock_session = AsyncMock(spec=ClientSession)
    transport = McpHttpTransportV20250618(
        "http://fake-server.com", session=mock_session, protocol=Protocol.MCP_v20250618
    )
    yield transport
    await transport.close()


@pytest.mark.asyncio
class TestMcpHttpTransportV20250618:

    # --- Request Sending Tests (Standard + Header) ---

    async def test_send_request_success(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        result = await transport._send_request("url", TestRequest())
        assert result == TestResult()

    async def test_send_request_adds_protocol_header(self, transport):
        """Test that the MCP-Protocol-Version header is added."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        await transport._send_request("url", TestRequest())

        call_args = transport._session.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["MCP-Protocol-Version"] == "2025-06-18"

    async def test_send_request_api_error(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 500
        mock_response.text.return_value = "Error"
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        with pytest.raises(RuntimeError, match="API request failed"):
            await transport._send_request("url", TestRequest())

    async def test_send_request_mcp_error(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "error": {"code": -32601, "message": "Error"},
        }
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        with pytest.raises(RuntimeError, match="MCP request failed"):
            await transport._send_request("url", TestRequest())

    async def test_send_notification(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 204
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestNotification(types.MCPNotification):
            method: str = "notifications/test"
            params: dict = {}

        await transport._send_request("url", TestNotification())
        payload = transport._session.post.call_args.kwargs["json"]
        assert "id" not in payload

    # --- Initialization Tests ---

    @patch("toolbox_core.mcp_transport.v20250618.mcp.version")
    async def test_initialize_session_success(self, mock_version, transport, mocker):
        mock_version.__version__ = "1.2.3"
        mock_send = mocker.patch.object(
            transport, "_send_request", new_callable=AsyncMock
        )

        mock_send.side_effect = [
            types.InitializeResult(
                protocolVersion="2025-06-18",
                capabilities=types.ServerCapabilities(tools={"listChanged": True}),
                serverInfo=types.Implementation(name="test", version="1.0"),
            ),
            None,
        ]

        await transport._initialize_session()
        assert transport._server_version == "1.0"

    @patch("toolbox_core.mcp_transport.v20250618.mcp.version")
    async def test_initialize_session_custom_client_info(self, mock_version, transport, mocker):
        mock_version.__version__ = "1.2.3"

        # Override transport's client info
        transport._client_name = "custom-client"
        transport._client_version = "9.9.9"

        mock_send = mocker.patch.object(
            transport, "_send_request", new_callable=AsyncMock
        )

        async def side_effect(*args, **kwargs):
            request = kwargs.get("request")
            if isinstance(request, types.InitializeRequest):
                # Verify the client info in the request
                assert request.params.clientInfo.name == "custom-client"
                assert request.params.clientInfo.version == "9.9.9"

                return types.InitializeResult.model_validate(
                    {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {"name": "test", "version": "1.0"},
                    }
                )
            return None

        mock_send.side_effect = side_effect

        await transport._initialize_session()

    async def test_initialize_session_protocol_mismatch(self, transport, mocker):
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=types.InitializeResult(
                protocolVersion="2099-01-01",
                capabilities=types.ServerCapabilities(tools={"listChanged": True}),
                serverInfo=types.Implementation(name="test", version="1.0"),
            ),
        )

        with pytest.raises(RuntimeError, match="MCP version mismatch"):
            await transport._initialize_session()

    async def test_initialize_session_missing_tools_capability(self, transport, mocker):
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=types.InitializeResult(
                protocolVersion="2025-06-18",
                capabilities=types.ServerCapabilities(),
                serverInfo=types.Implementation(name="test", version="1.0"),
            ),
        )

        with pytest.raises(
            RuntimeError, match="Server does not support the 'tools' capability"
        ):
            await transport._initialize_session()

    async def test_ensure_initialized_passes_headers(self, transport):
        transport._initialize_session = AsyncMock()

        test_headers = {"X-Test": "123"}
        await transport._ensure_initialized(headers=test_headers)

        transport._initialize_session.assert_called_with(headers=test_headers)

    async def test_initialize_passes_headers_to_request(self, transport):
        transport._send_request = AsyncMock()
        transport._send_request.return_value = types.InitializeResult(
            protocolVersion="2025-06-18",
            capabilities=types.ServerCapabilities(tools={"listChanged": True}),
            serverInfo=types.Implementation(name="test", version="1.0"),
        )

        test_headers = {"Authorization": "Bearer token"}
        await transport._initialize_session(headers=test_headers)

        assert transport._send_request.call_count == 2

        init_call = transport._send_request.call_args_list[0]
        assert isinstance(init_call.kwargs["request"], types.InitializeRequest)
        assert init_call.kwargs["headers"] == test_headers

        notify_call = transport._send_request.call_args_list[1]
        assert isinstance(notify_call.kwargs["request"], types.InitializedNotification)
        assert notify_call.kwargs["headers"] == test_headers

    # --- Tool Management Tests ---

    async def test_tools_list_success(self, transport, mocker):
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=create_fake_tools_list_result(),
        )
        transport._server_version = "1.0"
        manifest = await transport.tools_list()
        assert isinstance(manifest, ManifestSchema)

    async def test_tools_list_with_toolset_name(self, transport, mocker):
        """Test listing tools with a specific toolset name updates the URL."""
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=create_fake_tools_list_result(),
        )
        transport._server_version = "1.0.0"

        manifest = await transport.tools_list(toolset_name="custom_toolset")

        assert isinstance(manifest, ManifestSchema)
        expected_url = transport.base_url + "custom_toolset"

        call_args = transport._send_request.call_args
        assert call_args.kwargs["url"] == expected_url
        assert isinstance(call_args.kwargs["request"], types.ListToolsRequest)
        assert call_args.kwargs["headers"] is None

    async def test_tool_invoke_success(self, transport, mocker):
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=types.CallToolResult(
                content=[types.TextContent(type="text", text="Result")]
            ),
        )
        result = await transport.tool_invoke("tool", {}, {})
        assert result == "Result"

    async def test_tool_get_success(self, transport, mocker):
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=create_fake_tools_list_result(),
        )
        transport._server_version = "1.0"
        manifest = await transport.tool_get("get_weather")
        assert "get_weather" in manifest.tools

    async def test_tool_invoke_multiple_json_objects(self, transport, mocker):
        # Mock _ensure_initialized to do nothing
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)

        # Mock _send_request to return multiple JSON objects as separate text content
        mock_response = types.CallToolResult(
            content=[
                types.TextContent(type="text", text='{"foo":"bar", "baz": "qux"}'),
                types.TextContent(type="text", text='{"foo":"quux", "baz":"corge"}'),
            ]
        )

        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Invoke tool
        result = await transport.tool_invoke("tool", {}, {})

        # Expected result: A JSON list containing the objects
        expected = '[{"foo":"bar", "baz": "qux"},{"foo":"quux", "baz":"corge"}]'

        assert result == expected

    async def test_tool_invoke_split_text(self, transport, mocker):
        # Verify that split text (not complete JSON objects) is still joined normally
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)

        mock_response = types.CallToolResult(
            content=[
                types.TextContent(type="text", text="Hello "),
                types.TextContent(type="text", text="World"),
            ]
        )
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        result = await transport.tool_invoke("tool", {}, {})
        assert result == "Hello World"

    async def test_tool_invoke_split_json_object(self, transport, mocker):
        # Verify that a split JSON object is joined correctly (not wrapped in list)
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)

        # "{"a": 1}" split as "{"a": " and "1}"
        mock_response = types.CallToolResult(
            content=[
                types.TextContent(type="text", text='{"a": '),
                types.TextContent(type="text", text="1}"),
            ]
        )
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        result = await transport.tool_invoke("tool", {}, {})
        assert result == '{"a": 1}'
