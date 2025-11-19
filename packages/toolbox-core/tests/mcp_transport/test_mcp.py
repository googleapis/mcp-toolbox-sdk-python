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
from typing import Any, Mapping, Optional
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from toolbox_core.mcp_transport.mcp import _McpHttpTransportBase


class ConcreteTransport(_McpHttpTransportBase):
    """A concrete class for testing the abstract base class."""

    async def _initialize_session(self):
        pass

    async def _send_request(self, *args, **kwargs) -> Any:
        pass

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        pass

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> Any:
        pass

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        return ""


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
