# Copyright 2026 Google LLC
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

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses

from toolbox_core.mcp_transport.v20260618 import types
from toolbox_core.mcp_transport.v20260618.mcp import McpHttpTransportV20260618
from toolbox_core.protocol import ManifestSchema, Protocol


def create_fake_tools_list_result():
    return types.ListToolsResult(
        tools=[
            {
                "name": "get_weather",
                "description": "Gets the weather.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            }
        ]
    )


@pytest_asyncio.fixture(
    params=[False, True], ids=["telemetry_disabled", "telemetry_enabled"]
)
async def transport(request, mocker):
    if request.param:
        mocker.patch("toolbox_core.mcp_transport.telemetry.TELEMETRY_AVAILABLE", True)
        mocker.patch(
            "toolbox_core.mcp_transport.telemetry.get_tracer", return_value=MagicMock()
        )
        mocker.patch(
            "toolbox_core.mcp_transport.telemetry.get_meter", return_value=MagicMock()
        )
        mocker.patch(
            "toolbox_core.mcp_transport.telemetry.create_operation_duration_histogram",
            return_value=MagicMock(),
        )
        mocker.patch(
            "toolbox_core.mcp_transport.telemetry.create_session_duration_histogram",
            return_value=MagicMock(),
        )
        mocker.patch(
            "toolbox_core.mcp_transport.telemetry.start_span",
            return_value=(MagicMock(), "00-traceparent", ""),
        )
        mocker.patch("toolbox_core.mcp_transport.telemetry.end_span")
        mocker.patch("toolbox_core.mcp_transport.telemetry.record_operation_duration")
        mocker.patch("toolbox_core.mcp_transport.telemetry.record_session_duration")
    mock_session = AsyncMock(spec=ClientSession)
    transport = McpHttpTransportV20260618(
        "http://fake-server.com",
        session=mock_session,
        protocol=Protocol.MCP_DRAFT,
        telemetry_enabled=request.param,
    )
    yield transport
    await transport.close()


@pytest.mark.asyncio
class TestMcpHttpTransportV20260618:

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
        assert headers["MCP-Protocol-Version"] == "DRAFT-2026-v1"
        assert headers["Mcp-Method"] == "method"
        assert "Mcp-Name" not in headers

    async def test_send_request_adds_mcp_name_header_for_tools_call(self, transport):
        """Test that the Mcp-Name header is added for tools/call."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestParams(types.BaseModel):
            name: str

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "tools/call"
            params: TestParams

            def get_result_model(self):
                return TestResult

        await transport._send_request(
            "url", TestRequest(params=TestParams(name="test_tool"))
        )

        call_args = transport._session.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Mcp-Method"] == "tools/call"
        assert headers["Mcp-Name"] == "test_tool"

    async def test_send_request_adds_mcp_name_header_for_prompts_get(self, transport):
        """Test that the Mcp-Name header is added for prompts/get."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestParams(types.BaseModel):
            name: str

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "prompts/get"
            params: TestParams

            def get_result_model(self):
                return TestResult

        await transport._send_request(
            "url", TestRequest(params=TestParams(name="test_prompt"))
        )

        call_args = transport._session.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Mcp-Method"] == "prompts/get"
        assert headers["Mcp-Name"] == "test_prompt"

    async def test_send_request_adds_mcp_name_header_for_resources_read(
        self, transport
    ):
        """Test that the Mcp-Name header is added for resources/read."""
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        class TestResult(types.BaseModel):
            pass

        class TestParams(types.BaseModel):
            uri: str

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "resources/read"
            params: TestParams

            def get_result_model(self):
                return TestResult

        await transport._send_request(
            "url", TestRequest(params=TestParams(uri="file:///test.txt"))
        )

        call_args = transport._session.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Mcp-Method"] == "resources/read"
        assert headers["Mcp-Name"] == "file:///test.txt"

    # --- Version Negotiation Tests ---

    async def test_version_negotiation_raises_fallback(self, transport):
        """Tests that the client raises ProtocolNegotiationError when the server requests a fallback."""
        from toolbox_core.exceptions import ProtocolNegotiationError

        mock_response_reject = AsyncMock()
        mock_response_reject.ok = False
        mock_response_reject.status = 400
        mock_response_reject.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "error": {
                "code": -32022,
                "message": "Unsupported protocol version",
                "data": {"supported": ["DRAFT-2026-v1"]},
            },
        }

        transport._session.post.return_value.__aenter__.return_value = (
            mock_response_reject
        )

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        with pytest.raises(ProtocolNegotiationError) as exc_info:
            await transport._send_request("url", TestRequest())

        assert exc_info.value.negotiated_version == "DRAFT-2026-v1"
        assert transport._session.post.call_count == 1

    async def test_version_negotiation_raises_fallback_200_ok(self, transport):
        """Tests that the client raises ProtocolNegotiationError when the server returns 200 OK with -32022."""
        from toolbox_core.exceptions import ProtocolNegotiationError

        mock_response_reject = AsyncMock()
        mock_response_reject.ok = True
        mock_response_reject.status = 200
        mock_response_reject.content.at_eof = MagicMock(return_value=False)
        mock_response_reject.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "error": {
                "code": -32022,
                "message": "Unsupported protocol version",
                "data": {"supported": ["DRAFT-2026-v1"]},
            },
        }

        transport._session.post.return_value.__aenter__.return_value = (
            mock_response_reject
        )

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        with pytest.raises(ProtocolNegotiationError) as exc_info:
            await transport._send_request("url", TestRequest())

        assert exc_info.value.negotiated_version == "DRAFT-2026-v1"
        assert transport._session.post.call_count == 1

    async def test_version_negotiation_empty_intersection(self, transport):
        """Tests that the client errors immediately without retrying when there is no mutual version."""
        mock_response_reject = AsyncMock()
        mock_response_reject.ok = False
        mock_response_reject.status = 400
        mock_response_reject.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "error": {
                "code": -32022,
                "message": "Unsupported protocol version",
                "data": {"supported": ["UNSUPPORTED-VERSION"]},
            },
        }

        transport._session.post.return_value.__aenter__.return_value = (
            mock_response_reject
        )

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        with pytest.raises(
            RuntimeError, match="No mutually supported protocol version"
        ):
            await transport._send_request("url", TestRequest())

        assert transport._session.post.call_count == 1

    # --- Tool Management Tests ---

    async def test_tools_list_success(self, transport, mocker):
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=create_fake_tools_list_result(),
        )
        manifest = await transport.tools_list()
        assert isinstance(manifest, ManifestSchema)
        assert "get_weather" in manifest.tools

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

    async def test_send_request_400_with_json_rpc_error(self, transport):
        # Test that an HTTP 400 with a non-negotiation JSON-RPC error is parsed properly.
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 400
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "missing _meta"},
        }

        transport._session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await transport._send_request(
                "http://test.com/mcp",
                types.JSONRPCRequest(method="test", params={}),
            )

        assert "MCP request failed with code -32602" in str(exc_info.value)
        assert "missing _meta" in str(exc_info.value)

    async def test_send_request_400_with_raw_text(self, transport):
        # Test that an HTTP 400 with non-JSON text is raised with the raw string payload.
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 400
        mock_response.reason = "Bad Request"
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text.return_value = "<html/>"

        transport._session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await transport._send_request(
                "http://test.com/mcp",
                types.JSONRPCRequest(method="test", params={}),
            )

        assert "API request failed with status 400" in str(exc_info.value)
        assert "<html/>" in str(exc_info.value)

    async def test_version_negotiation_legacy_string_fallback(self, transport):
        """Tests that the client raises ProtocolNegotiationError when the server returns a string 'invalid protocol version' error."""
        from toolbox_core.exceptions import ProtocolNegotiationError

        mock_response_reject = AsyncMock()
        mock_response_reject.ok = False
        mock_response_reject.status = 400
        mock_response_reject.json.return_value = {
            "jsonrpc": "2.0",
            "id": "1",
            "error": "invalid protocol version",
        }

        transport._session.post.return_value.__aenter__.return_value = (
            mock_response_reject
        )

        class TestResult(types.BaseModel):
            pass

        class TestRequest(types.MCPRequest[TestResult]):
            method: str = "method"
            params: dict = {}

            def get_result_model(self):
                return TestResult

        # The fallback defaults to picking the next version in the supported list, or 2025-11-25.
        with pytest.raises(ProtocolNegotiationError) as exc_info:
            await transport._send_request("url", TestRequest())

        assert exc_info.value.negotiated_version == Protocol.MCP_v20251125
        assert transport._session.post.call_count == 1
