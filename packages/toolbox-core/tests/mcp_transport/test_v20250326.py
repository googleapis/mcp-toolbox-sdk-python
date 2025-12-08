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

from toolbox_core.mcp_transport.v20250326.mcp import McpHttpTransportV20250326
from toolbox_core.protocol import ManifestSchema, Protocol


def create_fake_tools_list_result():
    return {
        "tools": [
            {"name": "get_weather", "inputSchema": {"type": "object", "properties": {}}}
        ]
    }


@pytest_asyncio.fixture
async def transport():
    mock_session = AsyncMock(spec=ClientSession)
    transport = McpHttpTransportV20250326(
        "http://fake-server.com", session=mock_session, protocol=Protocol.MCP_v20250326
    )
    yield transport
    await transport.close()


@pytest.mark.asyncio
class TestMcpHttpTransportV20250326:
    # --- Request Sending Tests (Standard + Session ID) ---

    async def test_send_request_success(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        result = await transport._send_request("url", "method", {})
        assert result == {}

    async def test_send_request_with_session_id(self, transport):
        """Test that the session ID is injected into params."""
        transport._session_id = "test-session-id"
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json.return_value = {"jsonrpc": "2.0", "id": "1", "result": {}}
        transport._session.post.return_value.__aenter__.return_value = mock_response

        await transport._send_request("url", "method", {"param": "value"})

        call_args = transport._session.post.call_args
        sent_params = call_args.kwargs["json"]["params"]
        assert sent_params["Mcp-Session-Id"] == "test-session-id"
        assert sent_params["param"] == "value"

    async def test_send_request_api_error(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 500
        mock_response.text.return_value = "Error"
        transport._session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(RuntimeError, match="API request failed"):
            await transport._send_request("url", "method", {})

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

        with pytest.raises(RuntimeError, match="MCP request failed"):
            await transport._send_request("url", "method", {})

    async def test_send_notification(self, transport):
        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.status = 204
        transport._session.post.return_value.__aenter__.return_value = mock_response

        await transport._send_request("url", "notifications/test", {})
        payload = transport._session.post.call_args.kwargs["json"]
        assert "id" not in payload

    # --- Initialization Tests (Session ID Required) ---

    @patch("toolbox_core.mcp_transport.v20250326.mcp.version")
    async def test_initialize_session_success(self, mock_version, transport, mocker):
        mock_version.__version__ = "1.2.3"
        mock_send = mocker.patch.object(
            transport, "_send_request", new_callable=AsyncMock
        )

        mock_send.side_effect = [
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "test", "version": "1.0"},
                "Mcp-Session-Id": "sess-123",  # Required for this version
            },
            None,
        ]

        await transport._initialize_session()
        assert transport._session_id == "sess-123"

    async def test_initialize_session_missing_session_id(self, transport, mocker):
        """Specific test for 2025-03-26: Error if session ID is missing."""
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value={
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "test", "version": "1.0"},
            },
        )
        # Mock close since it will be called on failure
        mocker.patch.object(transport, "close", new_callable=AsyncMock)

        with pytest.raises(
            RuntimeError, match="Server did not return a Mcp-Session-Id"
        ):
            await transport._initialize_session()

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
        transport._send_request.assert_called_with(
            url=expected_url, method="tools/list", params={}, headers=None
        )

    async def test_tool_invoke_success(self, transport, mocker):
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value={"content": [{"type": "text", "text": "Result"}]},
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
