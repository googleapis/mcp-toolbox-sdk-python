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

from unittest.mock import AsyncMock

import pytest

from toolbox_core.mcp_transport.v20241105 import types as types_v20241105
from toolbox_core.mcp_transport.v20241105.mcp import McpHttpTransportV20241105
from toolbox_core.mcp_transport.v20250326 import types as types_v20250326
from toolbox_core.mcp_transport.v20250326.mcp import McpHttpTransportV20250326
from toolbox_core.mcp_transport.v20250618 import types as types_v20250618
from toolbox_core.mcp_transport.v20250618.mcp import McpHttpTransportV20250618
from toolbox_core.protocol import Protocol

TEST_CASES = [
    (
        McpHttpTransportV20241105,
        Protocol.MCP_v20241105,
        types_v20241105,
        "2024-11-05",
    ),
    (
        McpHttpTransportV20250326,
        Protocol.MCP_v20250326,
        types_v20250326,
        "2025-03-26",
    ),
    (
        McpHttpTransportV20250618,
        Protocol.MCP_v20250618,
        types_v20250618,
        "2025-06-18",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "TransportClass, protocol_enum, types_module, protocol_version_str", TEST_CASES
)
async def test_ensure_initialized_passes_headers(
    TransportClass, protocol_enum, types_module, protocol_version_str
):
    mock_session = AsyncMock()
    transport = TransportClass(
        "http://fake.com", session=mock_session, protocol=protocol_enum
    )

    transport._initialize_session = AsyncMock()

    test_headers = {"X-Test": "123"}
    await transport._ensure_initialized(headers=test_headers)

    transport._initialize_session.assert_called_with(headers=test_headers)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "TransportClass, protocol_enum, types_module, protocol_version_str", TEST_CASES
)
async def test_initialize_passes_headers_to_request(
    TransportClass, protocol_enum, types_module, protocol_version_str
):
    mock_session = AsyncMock()
    transport = TransportClass(
        "http://fake.com", session=mock_session, protocol=protocol_enum
    )

    # Mock _send_request to simulate successful init
    transport._send_request = AsyncMock()
    transport._send_request.return_value = types_module.InitializeResult(
        protocolVersion=protocol_version_str,
        capabilities=types_module.ServerCapabilities(
            tools={"listChanged": True}
        ),
        serverInfo=types_module.Implementation(name="test", version="1.0"),
    )

    # Mock session ID injection which happens in _send_request usually,
    # but here we just set it manually to satisfy the check for v20250326
    if isinstance(transport, McpHttpTransportV20250326):
        transport._session_id = "test-session"

    test_headers = {"Authorization": "Bearer token"}
    await transport._initialize_session(headers=test_headers)

    # Verify calls
    assert transport._send_request.call_count == 2

    # First call: InitializeRequest
    init_call = transport._send_request.call_args_list[0]
    assert isinstance(init_call.kwargs["request"], types_module.InitializeRequest)
    assert init_call.kwargs["headers"] == test_headers

    # Second call: InitializedNotification
    notify_call = transport._send_request.call_args_list[1]
    assert isinstance(
        notify_call.kwargs["request"], types_module.InitializedNotification
    )
    assert notify_call.kwargs["headers"] == test_headers
