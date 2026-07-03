import pytest
from unittest.mock import AsyncMock, patch
from toolbox_core.client import _McpTransportProxy
from toolbox_core.protocol import Protocol
from toolbox_core.exceptions import ProtocolNegotiationError

@pytest.mark.asyncio
async def test_artificial_array():
    """The Artificial Array Test: simulate server returning 2025-03-26, should fallback to 2024-11-05."""
    proxy = _McpTransportProxy("http://mock", None, Protocol.MCP_DRAFT, None, None, False, [Protocol.MCP_DRAFT.value, Protocol.MCP_v20241105.value])
    
    proxy._active_transport.tool_get = AsyncMock(side_effect=ProtocolNegotiationError(Protocol.MCP_v20250326.value))
    
    with patch.object(proxy, "_create_transport") as mock_create:
        mock_new_transport = AsyncMock()
        mock_new_transport.tool_get.return_value = "success"
        mock_create.return_value = mock_new_transport
        
        res = await proxy.tool_get("mock")
        
        assert res == "success"
        mock_create.assert_called_with(Protocol.MCP_v20241105)

@pytest.mark.asyncio
async def test_cascading_fallback():
    """The Cascading Fallback Test: simulate server stateless generic error which throws the next stateful version."""
    proxy = _McpTransportProxy("http://mock", None, Protocol.MCP_DRAFT, None, None, False, [Protocol.MCP_DRAFT.value, Protocol.MCP_v20251125.value])
    
    proxy._active_transport.tool_get = AsyncMock(side_effect=ProtocolNegotiationError(Protocol.MCP_v20251125.value))
    
    with patch.object(proxy, "_create_transport") as mock_create:
        mock_new_transport = AsyncMock()
        mock_new_transport.tool_get.return_value = "success"
        mock_create.return_value = mock_new_transport
        
        res = await proxy.tool_get("mock")
        
        assert res == "success"
        mock_create.assert_called_with(Protocol.MCP_v20251125)

@pytest.mark.asyncio
async def test_strict_constraint():
    """The Strict Constraint Test: simulate legacy server returning an unsupported old version."""
    proxy = _McpTransportProxy("http://mock", None, Protocol.MCP_DRAFT, None, None, False, [Protocol.MCP_DRAFT.value, Protocol.MCP_v20251125.value])
    
    proxy._active_transport.tool_get = AsyncMock(side_effect=ProtocolNegotiationError(Protocol.MCP_v20241105.value))
    
    with pytest.raises(RuntimeError, match="No mutually supported protocol version"):
        await proxy.tool_get("mock")

@pytest.mark.asyncio
async def test_modern_smart_fallback():
    """The Modern Smart-Fallback Test: simulate modern payload correctly returning pre-intersected fallback."""
    proxy = _McpTransportProxy("http://mock", None, Protocol.MCP_DRAFT, None, None, False, [Protocol.MCP_DRAFT.value, Protocol.MCP_v20241105.value])
    
    proxy._active_transport.tool_get = AsyncMock(side_effect=ProtocolNegotiationError(Protocol.MCP_v20241105.value))
    
    with patch.object(proxy, "_create_transport") as mock_create:
        mock_new_transport = AsyncMock()
        mock_new_transport.tool_get.return_value = "success"
        mock_create.return_value = mock_new_transport
        
        res = await proxy.tool_get("mock")
        
        assert res == "success"
        mock_create.assert_called_with(Protocol.MCP_v20241105)
