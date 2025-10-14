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

from toolbox_core.mcp_transport.transport_base import _McpHttpTransportBase
from toolbox_core.protocol import ToolSchema


class ConcreteTransport(_McpHttpTransportBase):
    """A concrete class for testing the abstract base class."""

    async def _initialize_session(self):
        pass

    async def _send_request(self, *args, **kwargs) -> Any:
        pass

    async def tools_list(self, *args, **kwargs):
        pass

    async def tool_get(self, *args, **kwargs):
        pass

    async def tool_invoke(self, *args, **kwargs):
        pass


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
    async def test_initialization_properties(self, transport):
        """Test constructor properties are set correctly."""
        assert transport.base_url == "http://fake-server.com/mcp/"
        assert transport._manage_session is True
        assert transport._session is not None

    @pytest.mark.asyncio
    async def test_ensure_initialized_calls_initialize(self, transport, mocker):
        """Test that _ensure_initialized calls _initialize_session."""
        mocker.patch.object(transport, "_initialize_session", new_callable=AsyncMock)
        await transport._ensure_initialized()
        transport._initialize_session.assert_called_once()

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
        """Test that _ensure_initialized calls _initialize_session."""
        await transport._ensure_initialized()
        transport._initialize_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_is_only_run_once(self, transport):
        """Test the lock ensures initialization only happens once with concurrent calls."""
        init_started = asyncio.Event()

        async def slow_init():
            init_started.set()
            await asyncio.sleep(0.01)

        transport._initialize_session.side_effect = slow_init

        task1 = asyncio.create_task(transport._ensure_initialized())
        await init_started.wait()
        task2 = asyncio.create_task(transport._ensure_initialized())
        await asyncio.gather(task1, task2)

        transport._initialize_session.assert_called_once()

    def test_convert_tool_schema_valid(self, transport):
        """Test converting a valid MCP tool schema."""
        raw_tool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string", "description": "Argument 1"},
                    "arg2": {"type": "integer"},
                },
                "required": ["arg1"],
            },
        }

        schema = transport._convert_tool_schema(raw_tool)

        assert isinstance(schema, ToolSchema)
        assert schema.description == "A test tool"
        assert len(schema.parameters) == 2

        p1 = next(p for p in schema.parameters if p.name == "arg1")
        assert p1.type == "string"
        assert p1.description == "Argument 1"
        assert p1.required is True

        p2 = next(p for p in schema.parameters if p.name == "arg2")
        assert p2.type == "integer"
        assert p2.required is False

    def test_convert_tool_schema_complex_types(self, transport):
        """Test converting schema with array and object types."""
        raw_tool = {
            "name": "complex_tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "list_param": {"type": "array", "items": {"type": "string"}},
                    "obj_param": {
                        "type": "object",
                        "additionalProperties": {"type": "integer"},
                    },
                },
            },
        }

        schema = transport._convert_tool_schema(raw_tool)
        p_list = next(p for p in schema.parameters if p.name == "list_param")
        assert p_list.type == "array"

        p_obj = next(p for p in schema.parameters if p.name == "obj_param")
        assert p_obj.type == "object"
        assert p_obj.additionalProperties.type == "integer"

    @pytest.mark.asyncio
    async def test_close_managed_session(self, mocker):
        mock_close = mocker.patch("aiohttp.ClientSession.close", new_callable=AsyncMock)
        transport = ConcreteTransport("http://fake-server.com")
        # Mock the init task so close() tries to await it
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