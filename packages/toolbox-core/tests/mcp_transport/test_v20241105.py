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

from toolbox_core.mcp_transport.v20241105.mcp import McpHttpTransport_v20241105
from toolbox_core.protocol import ManifestSchema, Protocol


def create_fake_tools_list_result():
    return {
        "tools": [
            {
                "name": "get_weather",
                "description": "Gets the weather.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The location."}
                    },
                    "required": ["location"],
                },
            }
        ]
    }


@pytest_asyncio.fixture
async def transport():
    """Creates a transport instance with a mocked session."""
    mock_session = AsyncMock(spec=ClientSession)
    transport_instance = McpHttpTransport_v20241105(
        "http://fake-server.com", session=mock_session, protocol=Protocol.MCP_v20241105
    )
    transport_instance._session = mock_session
    yield transport_instance
    await transport_instance.close()


@pytest.mark.asyncio
class TestMcpHttpTransport_v20241105:
    async def test_send_request_success(self, transport):
        """Test a successful request."""
        mock_response = transport._session.post.return_value.__aenter__.return_value
        mock_response.ok = True
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json = AsyncMock(
            return_value={"jsonrpc": "2.0", "id": "1", "result": {"status": "success"}}
        )

        result = await transport._send_request(
            "http://fake-server.com/mcp/", "test/method", {}
        )
        assert result == {"status": "success"}
        transport._session.post.assert_called_once()

    async def test_send_request_api_error(self, transport):
        """Test a request that fails with an API error."""
        mock_response = transport._session.post.return_value.__aenter__.return_value
        mock_response.ok = False
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = AsyncMock(return_value="Error details")

        with pytest.raises(RuntimeError, match="API request failed with status 500"):
            await transport._send_request(
                "http://fake-server.com/mcp/", "test/method", {}
            )

    async def test_send_request_mcp_error(self, transport):
        """Test a request that returns an MCP error."""
        mock_response = transport._session.post.return_value.__aenter__.return_value
        mock_response.ok = True
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": "1",
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

        with pytest.raises(RuntimeError, match="MCP request failed"):
            await transport._send_request(
                "http://fake-server.com/mcp/", "test/method", {}
            )

    @patch("toolbox_core.mcp_transport.v20241105.mcp.version")
    async def test_initialize_session(self, mock_version, transport, mocker):
        """Test the session initialization process."""
        mock_version.__version__ = "1.2.3"
        mocker.patch.object(
            transport,
            "_perform_initialization_and_negotiation",
            new_callable=AsyncMock,
        )
        mocker.patch.object(transport, "_send_request", new_callable=AsyncMock)

        await transport._initialize_session()

        transport._perform_initialization_and_negotiation.assert_called_once()
        transport._send_request.assert_called_once_with(
            url=transport.base_url, method="notifications/initialized", params={}
        )

    async def test_tools_list_success(self, transport, mocker):
        """Test listing tools."""
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        # Mock _send_request to return the result payload directly
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value=create_fake_tools_list_result(),
        )
        transport._server_version = "1.0.0"

        manifest = await transport.tools_list()

        assert isinstance(manifest, ManifestSchema)
        assert "get_weather" in manifest.tools
        transport._send_request.assert_called_with(
            url=transport.base_url, method="tools/list", params={}, headers=None
        )

    async def test_tool_invoke_success(self, transport, mocker):
        """Test invoking a tool."""
        mocker.patch.object(transport, "_ensure_initialized", new_callable=AsyncMock)
        mocker.patch.object(
            transport,
            "_send_request",
            new_callable=AsyncMock,
            return_value={"content": [{"type": "text", "text": "Sunny"}]},
        )

        result = await transport.tool_invoke("get_weather", {"loc": "US"}, {})
        assert result == "Sunny"
