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

from typing import AsyncGenerator
import pytest
import pytest_asyncio
import nest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses

from toolbox_core.mcp_transport import McpHttpTransport
from toolbox_core.protocol import ManifestSchema, Protocol

nest_asyncio.apply()
TEST_BASE_URL = "http://fake-mcp-server.com"
TEST_TOOL_NAME = "test_tool"


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """Provides a real aiohttp ClientSession that is closed after the test."""
    async with ClientSession() as session:
        yield session


@pytest.fixture
def mock_initialize_response() -> dict:
    """Provides a valid sample dictionary for an initialize response."""
    # Return a copy to ensure tests can modify the dictionary without affecting others
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {
            "serverInfo": {
                "name": "Fake MCP Server",
                "version": "1.0.0",
                "protocolVersion": "2025-06-18",
            },
            "capabilities": {"tools": {}},
        },
    }


@pytest.fixture
def mock_tools_list_response() -> dict:
    """Provides a valid sample dictionary for a tools/list response."""
    return {
        "jsonrpc": "2.0",
        "id": "2",
        "result": {
            "tools": [
                {
                    "name": TEST_TOOL_NAME,
                    "description": "A test tool",
                    "parameters": [
                        {
                            "name": "param1",
                            "type": "string",
                            "description": "A parameter",
                            "required": True,
                        }
                    ],
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_successful_initialization(
    http_session: ClientSession, mock_initialize_response: dict
):
    """Tests that the transport initializes without errors."""
    url = f"{TEST_BASE_URL}/mcp/"
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        # Mock the second (initialized) call
        m.post(url, status=200, payload={"jsonrpc": "2.0", "id": "3", "result": {}})

        # This will call __init__ which runs the async _initialize_session synchronously
        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )
        assert transport.base_url == TEST_BASE_URL


@pytest.mark.asyncio
async def test_tools_list_success(
    http_session: ClientSession,
    mock_initialize_response: dict,
    mock_tools_list_response: dict,
):
    """Tests a successful tools_list call."""
    url = f"{TEST_BASE_URL}/mcp/"
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})  # Initialized notification

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )

        # Mock the actual tools/list call
        m.post(f"{TEST_BASE_URL}/mcp", status=200, payload=mock_tools_list_response)
        result = await transport.tools_list()

        assert isinstance(result, ManifestSchema)
        assert result.serverVersion == "1.0.0"
        assert TEST_TOOL_NAME in result.tools


@pytest.mark.asyncio
async def test_tool_get_success(
    http_session: ClientSession,
    mock_initialize_response: dict,
    mock_tools_list_response: dict,
):
    """Tests getting a single existing tool."""
    url = f"{TEST_BASE_URL}/mcp/"
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )

        m.post(f"{TEST_BASE_URL}/mcp", status=200, payload=mock_tools_list_response)
        result = await transport.tool_get(TEST_TOOL_NAME)

        assert len(result.tools) == 1
        assert TEST_TOOL_NAME in result.tools


@pytest.mark.asyncio
async def test_tool_get_not_found_raises_error(
    http_session: ClientSession,
    mock_initialize_response: dict,
    mock_tools_list_response: dict,
):
    """Tests that getting a non-existent tool raises ValueError."""
    url = f"{TEST_BASE_URL}/mcp/"
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )

        m.post(f"{TEST_BASE_URL}/mcp", status=200, payload=mock_tools_list_response)
        with pytest.raises(ValueError, match="Tool 'non_existent_tool' not found."):
            await transport.tool_get("non_existent_tool")


@pytest.mark.asyncio
async def test_tool_invoke_success(
    http_session: ClientSession, mock_initialize_response: dict
):
    """Tests a successful tool_invoke call."""
    url = f"{TEST_BASE_URL}/mcp/"
    invoke_response = {"jsonrpc": "2.0", "id": "4", "result": {"output": "success"}}
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )

        m.post(url, status=200, payload=invoke_response)
        result = await transport.tool_invoke(TEST_TOOL_NAME, {"arg": "val"}, {})
        assert result == {"output": "success"}


@pytest.mark.asyncio
async def test_http_request_failure(
    http_session: ClientSession, mock_initialize_response: dict
):
    """Tests that a non-200 response raises a RuntimeError."""
    url = f"{TEST_BASE_URL}/mcp/"
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )
        m.post(f"{TEST_BASE_URL}/mcp", status=500, body="Internal Server Error")
        with pytest.raises(RuntimeError) as exc_info:
            await transport.tools_list()

    assert "API request failed with status 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_json_rpc_error(
    http_session: ClientSession, mock_initialize_response: dict
):
    """Tests that a response with a JSON-RPC error raises a RuntimeError."""
    url = f"{TEST_BASE_URL}/mcp/"
    error_response = {
        "jsonrpc": "2.0",
        "id": "5",
        "error": {"code": -32601, "message": "Method not found"},
    }
    with aioresponses() as m:
        m.post(url, status=200, payload=mock_initialize_response)
        m.post(url, status=200, payload={})

        transport = McpHttpTransport(
            base_url=TEST_BASE_URL,
            session=http_session,
            protocol=Protocol.MCP_LATEST,
        )
        m.post(f"{TEST_BASE_URL}/mcp", status=200, payload=error_response)

        with pytest.raises(RuntimeError, match="MCP request failed with code -32601"):
            await transport.tools_list()


# @pytest.mark.asyncio
# async def test_v2025_06_18_adds_protocol_header(
#     http_session: ClientSession,
#     mock_tools_list_response: dict,
#     mock_initialize_response: dict,
# ):
#     """Tests that MCP v2025-06-18 adds the MCP-Protocol-Version header."""
#     init_url = f"{TEST_BASE_URL}/mcp/"
#     list_url = f"{TEST_BASE_URL}/mcp"
#     protocol_version = "2025-06-18"

#     # Ensure the mock server responds with the desired protocol version
#     mock_initialize_response["result"]["serverInfo"]["protocolVersion"] = protocol_version

#     with aioresponses() as m:
#         # Mock the initialization sequence
#         m.post(init_url, status=200, payload=mock_initialize_response)
#         m.post(init_url, status=200, payload={})  # Initialized notification

#         # __init__ runs the real initialization, negotiating the version based on the mock response.
#         transport = McpHttpTransport(
#             base_url=TEST_BASE_URL,
#             session=http_session,
#             protocol=Protocol.MCP_v20250618,
#         )

#         # Mock the subsequent tools/list request
#         m.post(list_url, status=200, payload=mock_tools_list_response)
#         await transport.tools_list()

#         calls = m.requests.get(("POST", list_url))
#         assert calls is not None
#         assert len(calls) == 1
#         request = calls[0]
#         assert "MCP-Protocol-Version" in request.kwargs["headers"]
#         assert request.kwargs["headers"]["MCP-Protocol-Version"] == protocol_version

# @pytest.mark.asyncio
# async def test_v2025_03_26_session_id_handling(
#     http_session: ClientSession,
#     mock_tools_list_response: dict,
#     mock_initialize_response: dict,
# ):
#     """Tests that MCP v2025-03-26 correctly handles the session ID."""
#     session_id = "test-session-123"
#     init_url = f"{TEST_BASE_URL}/mcp/"
#     list_url = f"{TEST_BASE_URL}/mcp"
#     protocol_version = "2025-03-26"

#     # Configure the initialize response for v2025-03-26 and include the session ID
#     mock_initialize_response["result"]["serverInfo"]["protocolVersion"] = protocol_version
#     mock_initialize_response["result"]["Mcp-Session-Id"] = session_id

#     with aioresponses() as m:
#         # Mock the initialization sequence
#         m.post(init_url, status=200, payload=mock_initialize_response)
#         m.post(init_url, status=200, payload={})  # Initialized notification

#         # __init__ runs the real initialization and captures the session ID.
#         transport = McpHttpTransport(
#             base_url=TEST_BASE_URL,
#             session=http_session,
#             protocol=Protocol.MCP_v20250326,
#         )

#         # Mock the subsequent tools/list request
#         m.post(list_url, status=200, payload=mock_tools_list_response)
#         await transport.tools_list()

#         calls = m.requests.get(("POST", list_url))
#         assert calls is not None
#         assert len(calls) == 1
#         sent_payload = calls[0].kwargs["json"]
#         assert "Mcp-Session-Id" in sent_payload["params"]
#         assert sent_payload["params"]["Mcp-Session-Id"] == session_id


@pytest.mark.asyncio
async def test_v2025_03_26_missing_session_id_raises_error(
    http_session: ClientSession,
):
    """Tests that initialization fails for v2025-03-26 if no session ID is returned."""
    url = f"{TEST_BASE_URL}/mcp/"
    # Initialize response without a session ID
    init_response_no_session = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {
            "serverInfo": {
                "name": "Fake MCP Server",
                "version": "1.0.0",
                "protocolVersion": "2025-03-26",
            },
            "capabilities": {"tools": {}},
        },
    }

    with aioresponses() as m:
        m.post(url, status=200, payload=init_response_no_session)

        with pytest.raises(
            RuntimeError,
            match="Server did not return a Mcp-Session-Id during initialization.",
        ):
            McpHttpTransport(
                base_url=TEST_BASE_URL,
                session=http_session,
                protocol=Protocol.MCP_v20250326,
            )