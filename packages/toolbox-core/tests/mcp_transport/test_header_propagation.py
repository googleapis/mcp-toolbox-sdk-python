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

import pytest
from unittest.mock import AsyncMock
from toolbox_core.mcp_transport.v20250326.mcp import McpHttpTransportV20250326
from toolbox_core.protocol import Protocol
from toolbox_core.mcp_transport.v20250326 import types

@pytest.mark.asyncio
async def test_ensure_initialized_passes_headers():
    mock_session = AsyncMock()
    transport = McpHttpTransportV20250326(
        "http://fake.com", session=mock_session, protocol=Protocol.MCP_v20250326
    )
    
    transport._initialize_session = AsyncMock()
    
    test_headers = {"X-Test": "123"}
    await transport._ensure_initialized(headers=test_headers)
    
    transport._initialize_session.assert_called_with(headers=test_headers)

@pytest.mark.asyncio
async def test_initialize_passes_headers_to_request():
    mock_session = AsyncMock()
    transport = McpHttpTransportV20250326(
        "http://fake.com", session=mock_session, protocol=Protocol.MCP_v20250326
    )
    
    # Mock _send_request to simulate successful init
    transport._send_request = AsyncMock()
    transport._send_request.return_value = types.InitializeResult(
        protocolVersion="2025-03-26",
        capabilities=types.ServerCapabilities(tools={"listChanged": True}),
        serverInfo=types.Implementation(name="test", version="1.0"),
    )
    
    # Mock session ID injection which happens in _send_request usually, 
    # but here we just set it manually to satisfy the check
    transport._session_id = "test-session"

    test_headers = {"Authorization": "Bearer token"}
    await transport._initialize_session(headers=test_headers)

    # Verify calls
    assert transport._send_request.call_count == 2
    
    # First call: InitializeRequest
    init_call = transport._send_request.call_args_list[0]
    assert isinstance(init_call.kwargs["request"], types.InitializeRequest)
    assert init_call.kwargs["headers"] == test_headers
    
    # Second call: InitializedNotification
    notify_call = transport._send_request.call_args_list[1]
    assert isinstance(notify_call.kwargs["request"], types.InitializedNotification)
    assert notify_call.kwargs["headers"] == test_headers
