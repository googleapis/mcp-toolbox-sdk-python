# test_v20250326.py
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

from toolbox_core.mcp_transport.v20250326 import McpHttpTransport_v20250326


@pytest_asyncio.fixture
async def transport():
    """Creates a transport instance with a mocked session."""
    mock_session = AsyncMock(spec=ClientSession)
    transport_instance = McpHttpTransport_v20250326(
        "http://fake-server.com", session=mock_session
    )
    transport_instance._session = mock_session
    yield transport_instance
    await transport_instance.close()


@pytest.mark.asyncio
class TestMcpHttpTransport_v20250326:

    async def test_send_request_with_session_id(self, transport):
        """Test that the session ID is added to requests."""
        transport._session_id = "test-session-id"
        mock_response = transport._session.post.return_value.__aenter__.return_value
        mock_response.ok = True
        mock_response.content = Mock()
        mock_response.content.at_eof.return_value = False
        mock_response.json = AsyncMock(return_value={"result": "success"})

        await transport._send_request(
            "http://fake-server.com/mcp/", "test/method", {"param1": "value1"}
        )

        call_args = transport._session.post.call_args
        assert (
            call_args.kwargs["json"]["params"]["Mcp-Session-Id"] == "test-session-id"
        )

    @patch("toolbox_core.mcp_transport.v20250326.version")
    async def test_initialize_session_success(self, mock_version, transport, mocker):
        """Test successful session initialization and session ID handling."""
        mock_version.__version__ = "1.2.3"
        mock_init_and_negotiate = mocker.patch.object(
            transport,
            "_perform_initialization_and_negotiation",
            new_callable=AsyncMock,
            return_value={"Mcp-Session-Id": "new-session-id"},
        )
        mock_send_request = mocker.patch.object(
            transport, "_send_request", new_callable=AsyncMock
        )

        await transport._initialize_session()

        mock_init_and_negotiate.assert_called_once()
        assert transport._session_id == "new-session-id"
        mock_send_request.assert_called_once_with(
            url=transport.base_url, method="notifications/initialized", params={}
        )

    async def test_initialize_session_no_session_id(self, transport, mocker):
        """Test that an error is raised if no session ID is returned."""
        transport._manage_session = True
        
        mocker.patch.object(
            transport,
            "_perform_initialization_and_negotiation",
            new_callable=AsyncMock,
            return_value={},  # No session ID
        )
        mocker.patch.object(transport, "close", new_callable=AsyncMock)

        with pytest.raises(
            RuntimeError,
            match="Server did not return a Mcp-Session-Id during initialization.",
        ):
            await transport._initialize_session()

        transport.close.assert_called_once()