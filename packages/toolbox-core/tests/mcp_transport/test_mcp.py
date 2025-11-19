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
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from toolbox_core.mcp_transport.mcp import _McpHttpTransportBase
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

    def test_convert_tool_schema_with_auth_params(self, transport):
        raw_tool = {
            "name": "auth_tool",
            "description": "Tool with auth params",
            "_meta": {"toolbox/authParam": {"api_key": ["header", "X-API-Key"]}},
            "inputSchema": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "other_param": {"type": "string"},
                },
            },
        }

        schema = transport._convert_tool_schema(raw_tool)
        api_key_param = next(p for p in schema.parameters if p.name == "api_key")
        assert api_key_param.authSources == ["header", "X-API-Key"]
        other_param = next(p for p in schema.parameters if p.name == "other_param")
        assert other_param.authSources is None

    def test_convert_tool_schema_with_auth_invoke(self, transport):
        raw_tool = {
            "name": "invoke_auth_tool",
            "description": "Tool requiring invocation auth",
            "_meta": {"toolbox/authInvoke": ["Bearer", "OAuth2"]},
            "inputSchema": {"type": "object", "properties": {}},
        }

        schema = transport._convert_tool_schema(raw_tool)

        assert schema.authRequired == ["Bearer", "OAuth2"]

    def test_convert_tool_schema_multiple_auth_services(self, transport):
        """
        Test where a single parameter requires multiple/complex auth definitions,
        or multiple parameters have distinct auth requirements.
        """
        raw_tool = {
            "name": "multi_auth_tool",
            "description": "Tool with multiple auth params",
            "_meta": {
                "toolbox/authParam": {
                    "service_a_key": ["header", "X-Service-A-Key"],
                    "service_b_token": ["header", "X-Service-B-Token"],
                }
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "service_a_key": {"type": "string"},
                    "service_b_token": {"type": "string"},
                    "regular_param": {"type": "string"},
                },
            },
        }

        schema = transport._convert_tool_schema(raw_tool)
        param_a = next(p for p in schema.parameters if p.name == "service_a_key")
        assert param_a.authSources == ["header", "X-Service-A-Key"]
        param_b = next(p for p in schema.parameters if p.name == "service_b_token")
        assert param_b.authSources == ["header", "X-Service-B-Token"]
        regular = next(p for p in schema.parameters if p.name == "regular_param")
        assert regular.authSources is None

    def test_convert_tool_schema_mixed_auth_same_name(self, transport):
        """
        Test both toolbox/authParam and toolbox/authInvoke present,
        using the SAME auth definition (e.g., same Bearer token used for both).
        """
        raw_tool = {
            "name": "mixed_auth_same_tool",
            "description": "Tool with overlapping auth requirements",
            "_meta": {
                "toolbox/authInvoke": ["Bearer", "SharedToken"],
                "toolbox/authParam": {"auth_token": ["Bearer", "SharedToken"]},
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "auth_token": {"type": "string"},
                    "query": {"type": "string"},
                },
            },
        }

        schema = transport._convert_tool_schema(raw_tool)
        assert schema.authRequired == ["Bearer", "SharedToken"]
        param_auth = next(p for p in schema.parameters if p.name == "auth_token")
        assert param_auth.authSources == ["Bearer", "SharedToken"]

    def test_convert_tool_schema_mixed_auth_different_names(self, transport):
        """
        Test both toolbox/authParam and toolbox/authInvoke present,
        but with DIFFERENT auth definitions (e.g. OAuth for the tool, API Key for a specific param).
        """
        raw_tool = {
            "name": "mixed_auth_diff_tool",
            "description": "Tool with distinct auth requirements",
            "_meta": {
                "toolbox/authInvoke": ["Bearer", "GoogleOAuth"],
                "toolbox/authParam": {"third_party_key": ["header", "X-3rd-Party-Key"]},
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "third_party_key": {"type": "string"},
                    "user_query": {"type": "string"},
                },
            },
        }

        schema = transport._convert_tool_schema(raw_tool)
        assert schema.authRequired == ["Bearer", "GoogleOAuth"]
        param_auth = next(p for p in schema.parameters if p.name == "third_party_key")
        assert param_auth.authSources == ["header", "X-3rd-Party-Key"]

        param_normal = next(p for p in schema.parameters if p.name == "user_query")
        assert param_normal.authSources is None

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
