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

"""OpenTelemetry telemetry utilities for MCP protocol.

This module implements telemetry following the MCP Semantic Conventions:
https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp

To enable telemetry, configure OpenTelemetry in YOUR application before using this library.
See module docstring below for configuration examples.

Note: OpenTelemetry is an optional dependency. Install with:
    pip install toolbox-core[telemetry]
"""

import logging
from typing import Any, Optional
from urllib.parse import urlparse

# Try to import OpenTelemetry - it's an optional dependency
try:
    from opentelemetry import metrics, trace
    from opentelemetry.metrics import Histogram, Meter
    from opentelemetry.trace import Span, SpanKind, Status, StatusCode, Tracer
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    # Define placeholder types to avoid NameError at import time
    Tracer = Any  # type: ignore[misc, assignment]
    Meter = Any  # type: ignore[misc, assignment]
    Histogram = Any  # type: ignore[misc, assignment]
    Span = Any  # type: ignore[misc, assignment]
    metrics = None  # type: ignore[assignment]
    trace = None  # type: ignore[assignment]
    SpanKind = None  # type: ignore[misc, assignment]
    Status = None  # type: ignore[misc, assignment]
    StatusCode = None  # type: ignore[misc, assignment]
    TraceContextTextMapPropagator = None  # type: ignore[misc, assignment]


def resolve_telemetry_enabled(enabled: bool) -> bool:
    """Resolve whether telemetry is active given the user flag and library availability."""
    return bool(enabled) and TELEMETRY_AVAILABLE


# Attribute names following MCP semantic conventions
ATTR_MCP_METHOD_NAME = "mcp.method.name"
ATTR_MCP_PROTOCOL_VERSION = "mcp.protocol.version"
ATTR_MCP_SESSION_ID = "mcp.session.id"
ATTR_ERROR_TYPE = "error.type"
ATTR_GEN_AI_TOOL_NAME = "gen_ai.tool.name"
ATTR_GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
ATTR_GEN_AI_PROMPT_NAME = "gen_ai.prompt.name"
ATTR_SERVER_ADDRESS = "server.address"
ATTR_SERVER_PORT = "server.port"
ATTR_NETWORK_TRANSPORT = "network.transport"
ATTR_NETWORK_PROTOCOL_NAME = "network.protocol.name"

# Metric names following MCP semantic conventions
METRIC_CLIENT_OPERATION_DURATION = "mcp.client.operation.duration"
METRIC_CLIENT_SESSION_DURATION = "mcp.client.session.duration"

# Histogram bucket boundaries for MCP metrics (in seconds)
# As specified in: https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/#metrics
MCP_DURATION_BUCKETS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]


def get_tracer(name: str = "toolbox.mcp.sdk", version: Optional[str] = None) -> Tracer:
    """Get a tracer from the global TracerProvider.

    This function retrieves a tracer from the globally configured TracerProvider.
    If no provider is configured by the application, OpenTelemetry returns a
    no-op tracer (zero overhead, no data collected).

    Args:
        name: The instrumentation scope name (default: "toolbox.mcp.sdk")
        version: The instrumentation scope version

    Returns:
        An OpenTelemetry Tracer instance (real or no-op depending on app config),
        or None if telemetry is not available

    Raises:
        RuntimeError: If OpenTelemetry is not installed
    """
    if not TELEMETRY_AVAILABLE:
        raise RuntimeError(
            "Telemetry support requires OpenTelemetry. Install with: "
            "pip install toolbox-core[telemetry]"
        )
    return trace.get_tracer(name, version)


def get_meter(name: str = "toolbox.mcp.sdk", version: Optional[str] = None) -> Meter:
    """Get a meter from the global MeterProvider.

    This function retrieves a meter from the globally configured MeterProvider.
    If no provider is configured by the application, OpenTelemetry returns a
    no-op meter (zero overhead, no data collected).

    Args:
        name: The instrumentation scope name (default: "toolbox.mcp.sdk")
        version: The instrumentation scope version

    Returns:
        An OpenTelemetry Meter instance (real or no-op depending on app config),
        or None if telemetry is not available

    Raises:
        RuntimeError: If OpenTelemetry is not installed
    """
    if not TELEMETRY_AVAILABLE:
        raise RuntimeError(
            "Telemetry support requires OpenTelemetry. Install with: "
            "pip install toolbox-core[telemetry]"
        )
    return metrics.get_meter(name, version or "")


def create_operation_duration_histogram(meter: Meter) -> Optional[Histogram]:
    """Create histogram for MCP client operation duration.

    Bucket boundaries are configured via Views in setup_telemetry() to match
    the MCP semantic conventions.

    Args:
        meter: The OpenTelemetry meter

    Returns:
        Histogram instance or None if creation failed
    """
    try:
        return meter.create_histogram(
            name=METRIC_CLIENT_OPERATION_DURATION,
            unit="s",
            description="Duration of MCP client operations (requests/notifications) from the time it was sent until the response or ack is received.",
            explicit_bucket_boundaries_advisory=MCP_DURATION_BUCKETS,
        )
    except Exception:
        return None


def create_session_duration_histogram(meter: Meter) -> Optional[Histogram]:
    """Create histogram for MCP client session duration.

    Bucket boundaries are configured via Views in setup_telemetry() to match
    the MCP semantic conventions.

    Args:
        meter: The OpenTelemetry meter

    Returns:
        Histogram instance or None if creation failed
    """
    try:
        return meter.create_histogram(
            name=METRIC_CLIENT_SESSION_DURATION,
            unit="s",
            description="Total duration of MCP client sessions",
            explicit_bucket_boundaries_advisory=MCP_DURATION_BUCKETS,
        )
    except Exception:
        return None


def extract_server_info(url: str) -> tuple[str, Optional[int], str]:
    """Extract server address, port, and protocol from URL.

    Args:
        url: The server URL

    Returns:
        Tuple of (server_address, server_port, protocol_name)
    """
    parsed = urlparse(url)
    protocol_name = parsed.scheme if parsed.scheme else "http"
    return parsed.hostname or parsed.netloc, parsed.port, protocol_name


def create_traceparent_from_context() -> str:
    """Create W3C traceparent header from current trace context.

    Returns:
        W3C traceparent header string in format:
        version-trace_id-parent_id-trace_flags
        Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
        Empty string if telemetry is not available.
    """
    if not TELEMETRY_AVAILABLE:
        return ""
    propagator = TraceContextTextMapPropagator()
    carrier: dict[str, str] = {}
    propagator.inject(carrier)
    return carrier.get("traceparent", "")


def create_tracestate_from_context() -> str:
    """Create W3C tracestate header from current trace context.

    Returns:
        W3C tracestate header string, empty string if telemetry is not available.
    """
    if not TELEMETRY_AVAILABLE:
        return ""
    propagator = TraceContextTextMapPropagator()
    carrier: dict[str, str] = {}
    propagator.inject(carrier)
    return carrier.get("tracestate", "")


def start_span(
    tracer: Optional[Tracer],
    method_name: str,
    protocol_version: str,
    server_url: str,
    tool_name: Optional[str] = None,
    network_transport: Optional[str] = None,
) -> tuple[Optional[Span], str, str]:
    """Start a telemetry span for MCP operations and extract W3C propagation headers.

    The span is briefly activated to extract traceparent/tracestate for context
    propagation to the server, then deactivated. Use end_span() to close it.

    Args:
        tracer: The OpenTelemetry tracer, or None if telemetry is disabled
        method_name: The MCP method name (e.g., "tools/call", "tools/list")
        protocol_version: The MCP protocol version
        server_url: The MCP server URL
        tool_name: Optional tool name for tools/call operations
        network_transport: Optional network transport type ("tcp" for HTTP/HTTPS, "pipe" for stdio)

    Returns:
        Tuple of (span, traceparent, tracestate). span is None and strings are
        empty if telemetry failed.
    """
    if tracer is None:
        return None, "", ""
    span = None
    try:
        span_name = f"{method_name} {tool_name}" if tool_name else method_name
        span = tracer.start_span(span_name, kind=SpanKind.CLIENT)

        # Required: MCP method name
        span.set_attribute(ATTR_MCP_METHOD_NAME, method_name)
        span.set_attribute(ATTR_MCP_PROTOCOL_VERSION, protocol_version)

        # Extract server info and network protocol from URL
        server_address, server_port, protocol_name = extract_server_info(server_url)
        span.set_attribute(ATTR_SERVER_ADDRESS, server_address)
        span.set_attribute(ATTR_NETWORK_PROTOCOL_NAME, protocol_name)
        if server_port:
            span.set_attribute(ATTR_SERVER_PORT, server_port)

        # Network transport ("tcp" for HTTP/HTTPS, "pipe" for stdio)
        if network_transport:
            span.set_attribute(ATTR_NETWORK_TRANSPORT, network_transport)

        if tool_name:
            span.set_attribute(ATTR_GEN_AI_TOOL_NAME, tool_name)
        if method_name == "tools/call":
            span.set_attribute(ATTR_GEN_AI_OPERATION_NAME, "execute_tool")

        # Activate the span to extract W3C propagation headers.
        # The client span becomes the parent of the server span through this context.
        # See: https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/#context-propagation
        with trace.use_span(span, end_on_exit=False):
            traceparent = create_traceparent_from_context()
            tracestate = create_tracestate_from_context()

        return span, traceparent, tracestate
    except Exception as e:
        logging.warning("start_span failed due to %s", e)
        # Telemetry failed - clean up span if it was created to prevent memory leaks
        if span is not None:
            span.end()
        return None, "", ""


def end_span(span: Optional[Span], error: Optional[Exception] = None) -> None:
    """End a telemetry span. Safe to call with None span.

    Args:
        span: The span to end (can be None if telemetry failed)
        error: Optional exception if operation failed
    """
    if span is None:
        return
    try:
        if error:
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.set_attribute(ATTR_ERROR_TYPE, type(error).__name__)
        span.end()
    except Exception as e:
        logging.warning("end_span failed due to %s", e)


def record_error_from_jsonrpc(span: Span, error_code: int, error_message: str) -> None:
    """Record error information from JSON-RPC error response.

    Args:
        span: The span to record the error on
        error_code: The JSON-RPC error code
        error_message: The JSON-RPC error message
    """
    span.set_status(Status(StatusCode.ERROR, error_message))
    span.set_attribute(ATTR_ERROR_TYPE, f"jsonrpc.error.{error_code}")


def record_operation_duration(
    histogram: Optional[Histogram],
    duration_seconds: float,
    method_name: str,
    protocol_version: str,
    server_url: str,
    tool_name: Optional[str] = None,
    network_transport: Optional[str] = None,
    error: Optional[Exception] = None,
) -> None:
    """Record MCP client operation duration metric.

    Args:
        histogram: The operation duration histogram (can be None if metrics failed)
        duration_seconds: Duration of the operation in seconds
        method_name: The MCP method name (required attribute)
        protocol_version: The MCP protocol version (recommended attribute)
        server_url: The MCP server URL (for extracting server address/port)
        tool_name: Optional tool name for tools/call operations
        network_transport: Optional network transport type ("tcp" for HTTP/HTTPS)
        error: Optional exception if operation failed (for error.type attribute)
    """
    if histogram is None:
        return

    try:
        # Build attributes dict following MCP semantic conventions
        attributes: dict[str, Any] = {
            ATTR_MCP_METHOD_NAME: method_name,
            ATTR_MCP_PROTOCOL_VERSION: protocol_version,
        }

        # Extract and add server info
        server_address, server_port, protocol_name = extract_server_info(server_url)
        attributes[ATTR_SERVER_ADDRESS] = server_address
        attributes[ATTR_NETWORK_PROTOCOL_NAME] = protocol_name
        if server_port:
            attributes[ATTR_SERVER_PORT] = server_port

        # Add optional network transport
        if network_transport:
            attributes[ATTR_NETWORK_TRANSPORT] = network_transport

        # Add tool-related attributes for tools/call operations
        if tool_name:
            attributes[ATTR_GEN_AI_TOOL_NAME] = tool_name
        if method_name == "tools/call":
            attributes[ATTR_GEN_AI_OPERATION_NAME] = "execute_tool"

        # Add error type if operation failed
        if error:
            attributes[ATTR_ERROR_TYPE] = type(error).__name__

        histogram.record(duration_seconds, attributes)
    except Exception as e:
        logging.warning("record_operation_duration failed due to %s", e)


def record_session_duration(
    histogram: Optional[Histogram],
    duration_seconds: float,
    protocol_version: str,
    server_url: str,
    network_transport: Optional[str] = None,
    error: Optional[Exception] = None,
) -> None:
    """Record MCP client session duration metric.

    Args:
        histogram: The session duration histogram (can be None if metrics failed)
        duration_seconds: Duration of the session in seconds
        protocol_version: The MCP protocol version (recommended attribute)
        server_url: The MCP server URL (for extracting server address/port)
        network_transport: Optional network transport type ("tcp" for HTTP/HTTPS)
        error: Optional exception if session ended with error
    """
    if histogram is None:
        return

    try:
        # Build attributes dict following MCP semantic conventions
        attributes: dict[str, Any] = {
            ATTR_MCP_PROTOCOL_VERSION: protocol_version,
        }

        # Extract and add server info
        server_address, server_port, protocol_name = extract_server_info(server_url)
        attributes[ATTR_SERVER_ADDRESS] = server_address
        attributes[ATTR_NETWORK_PROTOCOL_NAME] = protocol_name
        if server_port:
            attributes[ATTR_SERVER_PORT] = server_port

        # Add optional network transport
        if network_transport:
            attributes[ATTR_NETWORK_TRANSPORT] = network_transport

        # Add error type if session ended with error
        if error:
            attributes[ATTR_ERROR_TYPE] = type(error).__name__

        histogram.record(duration_seconds, attributes)
    except Exception as e:
        logging.warning("record_session_duration failed due to %s", e)
