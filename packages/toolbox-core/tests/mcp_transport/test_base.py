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

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from toolbox_core.mcp_transport.base import _McpHttpTransportBase
from toolbox_core.protocol import ManifestSchema, ToolSchema


class ConcreteTransport(_McpHttpTransportBase):
    """A concrete class for testing the abstract base class."""

    async def _initialize_session(self):
        pass  # Will be mocked

    async def _send_request(self, *args, **kwargs) -> Any:
        pass  # Will be mocked


def create_fake_initialize_response(
    server_version="1.0.0", protocol_version="2025-06-18", capabilities={"tools": {}}
):
    return {
        "serverInfo": {"version": server_version},
        "protocolVersion": protocol_version,
        "capabilities": capabilities,
    }


def create_fake_tools_list_response():
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
            },
            {
                "name": "send_email",
                "description": "Sends an email.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipient": {"type": "string"},
                        "body": {"type": "string"},
                    },
                },
            },
        ]
    }


@pytest_asyncio.fixture
async def transport(mocker):
    """
    A pytest fixture that creates and tears down a ConcreteTransport instance
    for each test that uses it.
    """
    base_url = "http://fake-server.com"
    transport_instance = ConcreteTransport(base_url)
    mocker.patch.object(
        transport_instance, "_initialize_session", new_callable=AsyncMock
    )
    mocker.patch.object(transport_instance, "_send_request", new_callable=AsyncMock)

    yield transport_instance
    await transport_instance.close()


class TestMcpHttpTransportBase:

    @pytest.mark.asyncio
    async def test_initialization(self, transport):
        """Test constructor properties."""
        assert transport.base_url == "http://fake-server.com/mcp/"
        assert transport._manage_session is True
        assert isinstance(transport._session, ClientSession)

    @pytest.mark.asyncio
    async def test_initialization_with_external_session(self):
        """Test that an external session is used and not managed."""
        mock_session = AsyncMock(spec=ClientSession)
        transport = ConcreteTransport("http://fake-server.com", session=mock_session)
        assert transport._manage_session is False
        assert transport._session is mock_session
        await transport.close()

    @pytest.mark.asyncio
    async def test_ensure_initialized_is_called(self, transport):
        """Test that public methods trigger initialization."""

        async def init_side_effect():
            transport._server_version = "1.0.0"

        transport._initialize_session.side_effect = init_side_effect
        transport._send_request.return_value = create_fake_tools_list_response()

        await transport.tools_list()
        transport._initialize_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_is_only_run_once(self, transport):
        """Test the lock ensures initialization only happens once with concurrent calls."""
        init_started = asyncio.Event()

        async def slow_init():
            init_started.set()
            transport._server_version = "1.0.0"
            await asyncio.sleep(0.01)

        transport._initialize_session.side_effect = slow_init
        transport._send_request.return_value = create_fake_tools_list_response()

        task1 = asyncio.create_task(transport.tools_list())
        await init_started.wait()
        task2 = asyncio.create_task(transport.tools_list())
        await asyncio.gather(task1, task2)

        transport._initialize_session.assert_called_once()

    def test_convert_tool_schema(self, transport):
        """Test the conversion from MCP tool schema to internal ToolSchema."""
        tool_data = {
            "name": "get_weather",
            "description": "A test tool.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city."},
                    "unit": {"type": "string"},
                },
                "required": ["location"],
            },
        }
        tool_schema = transport._convert_tool_schema(tool_data)
        assert tool_schema.description == "A test tool."
        location_param = next(p for p in tool_schema.parameters if p.name == "location")
        assert location_param.required is True
        assert location_param.description == "The city."

    def test_convert_tool_schema_with_auth(self, transport):
        """Test schema conversion with authentication metadata."""
        tool_data = {
            "name": "drive_tool",
            "description": "A tool that requires auth.",
            "inputSchema": {"type": "object", "properties": {}},
            "_meta": {
                "toolbox/authInvoke": ["google"],
            },
        }
        tool_schema = transport._convert_tool_schema(tool_data)
        assert tool_schema.authRequired == ["google"]

    @pytest.mark.asyncio
    async def test_tools_list_success(self, transport):
        transport._server_version = "1.0.0"
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        transport._send_request.return_value = create_fake_tools_list_response()
        manifest = await transport.tools_list()
        transport._send_request.assert_called_once_with(
            url=transport.base_url, method="tools/list", params={}, headers=None
        )
        assert isinstance(manifest, ManifestSchema)

    @pytest.mark.asyncio
    async def test_tool_get_success(self, transport):
        transport._server_version = "1.0.0"
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        transport._send_request.return_value = create_fake_tools_list_response()
        manifest = await transport.tool_get("get_weather")
        assert len(manifest.tools) == 1

    @pytest.mark.asyncio
    async def test_tool_get_not_found(self, transport):
        transport._server_version = "1.0.0"
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        transport._send_request.return_value = create_fake_tools_list_response()
        with pytest.raises(ValueError, match="Tool 'non_existent_tool' not found."):
            await transport.tool_get("non_existent_tool")

    @pytest.mark.asyncio
    async def test_tool_invoke_success(self, transport):
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        transport._send_request.return_value = {
            "content": [{"type": "text", "text": "The weather is sunny."}]
        }
        result = await transport.tool_invoke(
            "get_weather", {"location": "London"}, headers={"X-Test": "true"}
        )
        assert result == "The weather is sunny."

    @pytest.mark.asyncio
    async def test_perform_initialization_and_negotiation_failure(self, transport):
        transport._send_request.return_value = {}
        with pytest.raises(RuntimeError, match="Server info not found"):
            await transport._perform_initialization_and_negotiation({})

    @pytest.mark.asyncio
    async def test_close_managed_session(self, mocker):
        mock_close = mocker.patch("aiohttp.ClientSession.close", new_callable=AsyncMock)
        transport = ConcreteTransport("http://fake-server.com")
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        await transport.close()
        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_unmanaged_session(self):
        mock_session = AsyncMock(spec=ClientSession)
        transport = ConcreteTransport("http://fake-server.com", session=mock_session)
        transport._init_task = asyncio.create_task(asyncio.sleep(0))
        await transport.close()
        mock_session.close.assert_not_called()