
import pytest
import warnings
from unittest.mock import MagicMock, patch
from toolbox_core.client import ToolboxClient
from toolbox_core.protocol import Protocol

def test_toolbox_client_deprecation_warning():
    """Test that initializing ToolboxClient with Protocol.TOOLBOX issues a DeprecationWarning."""
    # Mock ToolboxTransport to avoid aiohttp session creation and event loop requirements
    with patch("toolbox_core.client.ToolboxTransport") as mock_transport:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # Cause all warnings to always be triggered.
            
            # Initialize client with Deprecated Protocol
            client = ToolboxClient("http://localhost:5000", protocol=Protocol.TOOLBOX)
            
            # Verify warning
            assert len(w) > 0
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "deprecated" in str(w[-1].message)
            assert "March 4, 2026" in str(w[-1].message)

def test_toolbox_client_no_warning_on_mcp():
    """Test that initializing ToolboxClient with Protocol.MCP issues NO DeprecationWarning."""
    # Mock the transport to avoid actual connection attempts or MCP version warnings
    with patch("toolbox_core.client.McpHttpTransportV20250618") as mock_transport:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            client = ToolboxClient("http://localhost:5000", protocol=Protocol.MCP)
            assert len(w) == 0

def test_toolbox_client_no_warning_on_explicit_mcp_version():
    """Test that specific MCP versions do not trigger the toolbox deprecation warning."""
    with patch("toolbox_core.client.McpHttpTransportV20251125") as mock_transport:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            client = ToolboxClient("http://localhost:5000", protocol=Protocol.MCP_v20251125)
            assert len(w) == 0
