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

from unittest.mock import ANY, MagicMock, patch

import pytest

import toolbox_core.mcp_transport.telemetry as telemetry_module
from toolbox_core.mcp_transport.telemetry import (
    ATTR_ERROR_TYPE,
    ATTR_GEN_AI_OPERATION_NAME,
    ATTR_GEN_AI_TOOL_NAME,
    ATTR_MCP_METHOD_NAME,
    ATTR_MCP_PROTOCOL_VERSION,
    ATTR_NETWORK_PROTOCOL_NAME,
    ATTR_NETWORK_TRANSPORT,
    ATTR_SERVER_ADDRESS,
    ATTR_SERVER_PORT,
    create_operation_duration_histogram,
    create_session_duration_histogram,
    create_traceparent_from_context,
    create_tracestate_from_context,
    end_span,
    extract_server_info,
    get_meter,
    get_tracer,
    record_error_from_jsonrpc,
    record_operation_duration,
    record_session_duration,
    start_span,
)


class TestGetTracer:
    def test_returns_tracer_when_available(self):
        mock_tracer = MagicMock()
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            with patch.object(telemetry_module, "trace") as mock_trace:
                mock_trace.get_tracer.return_value = mock_tracer
                result = get_tracer()
                mock_trace.get_tracer.assert_called_once_with("toolbox.mcp.sdk", None)
                assert result == mock_tracer

    def test_returns_tracer_with_custom_name_and_version(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            with patch.object(telemetry_module, "trace") as mock_trace:
                get_tracer("my.scope", "1.2.3")
                mock_trace.get_tracer.assert_called_once_with("my.scope", "1.2.3")

    def test_raises_when_unavailable(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pip install toolbox-core"):
                get_tracer()


class TestGetMeter:
    def test_returns_meter_when_available(self):
        mock_meter = MagicMock()
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            with patch.object(telemetry_module, "metrics") as mock_metrics:
                mock_metrics.get_meter.return_value = mock_meter
                result = get_meter()
                mock_metrics.get_meter.assert_called_once_with("toolbox.mcp.sdk", "")
                assert result == mock_meter

    def test_returns_meter_with_custom_name_and_version(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            with patch.object(telemetry_module, "metrics") as mock_metrics:
                get_meter("my.scope", "2.0.0")
                mock_metrics.get_meter.assert_called_once_with("my.scope", "2.0.0")

    def test_raises_when_unavailable(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="pip install toolbox-core"):
                get_meter()


class TestCreateOperationDurationHistogram:
    def test_creates_histogram_successfully(self):
        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram

        result = create_operation_duration_histogram(mock_meter)

        assert result == mock_histogram
        mock_meter.create_histogram.assert_called_once()

    def test_returns_none_on_exception(self):
        mock_meter = MagicMock()
        mock_meter.create_histogram.side_effect = Exception("failed")

        result = create_operation_duration_histogram(mock_meter)

        assert result is None


class TestCreateSessionDurationHistogram:
    def test_creates_histogram_successfully(self):
        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram

        result = create_session_duration_histogram(mock_meter)

        assert result == mock_histogram
        mock_meter.create_histogram.assert_called_once()

    def test_returns_none_on_exception(self):
        mock_meter = MagicMock()
        mock_meter.create_histogram.side_effect = Exception("failed")

        result = create_session_duration_histogram(mock_meter)

        assert result is None


class TestExtractServerInfo:
    def test_http_url_no_port(self):
        address, port, protocol = extract_server_info("http://example.com/path")
        assert address == "example.com"
        assert port is None
        assert protocol == "http"

    def test_https_url_with_port(self):
        address, port, protocol = extract_server_info("https://myserver.com:8443/mcp")
        assert address == "myserver.com"
        assert port == 8443
        assert protocol == "https"

    def test_http_url_with_port(self):
        address, port, protocol = extract_server_info("http://localhost:8080")
        assert address == "localhost"
        assert port == 8080
        assert protocol == "http"

    def test_url_no_scheme(self):
        address, port, protocol = extract_server_info("//example.com/path")
        assert protocol == "http"  # defaults to http when no scheme


class TestCreateTraceparentFromContext:
    def test_returns_empty_string_when_unavailable(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", False):
            result = create_traceparent_from_context()
            assert result == ""

    def test_returns_traceparent_when_available(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            mock_propagator = MagicMock()
            mock_propagator.inject.side_effect = lambda carrier: carrier.update(
                {"traceparent": "00-abc-def-01"}
            )
            with patch.object(
                telemetry_module,
                "TraceContextTextMapPropagator",
                return_value=mock_propagator,
            ):
                result = create_traceparent_from_context()
                assert result == "00-abc-def-01"

    def test_returns_empty_string_when_no_traceparent_in_carrier(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            mock_propagator = MagicMock()
            mock_propagator.inject.side_effect = lambda carrier: None
            with patch.object(
                telemetry_module,
                "TraceContextTextMapPropagator",
                return_value=mock_propagator,
            ):
                result = create_traceparent_from_context()
                assert result == ""


class TestCreateTracestateFromContext:
    def test_returns_empty_string_when_unavailable(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", False):
            result = create_tracestate_from_context()
            assert result == ""

    def test_returns_tracestate_when_available(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            mock_propagator = MagicMock()
            mock_propagator.inject.side_effect = lambda carrier: carrier.update(
                {"tracestate": "vendor=value"}
            )
            with patch.object(
                telemetry_module,
                "TraceContextTextMapPropagator",
                return_value=mock_propagator,
            ):
                result = create_tracestate_from_context()
                assert result == "vendor=value"

    def test_returns_empty_string_when_no_tracestate_in_carrier(self):
        with patch.object(telemetry_module, "TELEMETRY_AVAILABLE", True):
            mock_propagator = MagicMock()
            mock_propagator.inject.side_effect = lambda carrier: None
            with patch.object(
                telemetry_module,
                "TraceContextTextMapPropagator",
                return_value=mock_propagator,
            ):
                result = create_tracestate_from_context()
                assert result == ""


class TestStartSpan:
    def _make_tracer(self):
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        return mock_tracer, mock_span

    def _patch_trace(self):
        """Patch trace.use_span and SpanKind so tests work without opentelemetry."""
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        mock_trace = MagicMock()
        mock_trace.use_span.return_value = cm
        return patch.multiple(
            telemetry_module,
            trace=mock_trace,
            SpanKind=MagicMock(),
        )

    def test_basic_span_without_tool_name(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            result_span, traceparent, tracestate = start_span(
                tracer,
                method_name="tools/list",
                protocol_version="2025-06-18",
                server_url="http://example.com:8080",
            )
        assert result_span == span
        assert traceparent == ""
        assert tracestate == ""
        tracer.start_span.assert_called_once_with("tools/list", kind=ANY)
        span.set_attribute.assert_any_call(ATTR_MCP_METHOD_NAME, "tools/list")
        span.set_attribute.assert_any_call(ATTR_MCP_PROTOCOL_VERSION, "2025-06-18")
        span.set_attribute.assert_any_call(ATTR_SERVER_ADDRESS, "example.com")
        span.set_attribute.assert_any_call(ATTR_SERVER_PORT, 8080)
        span.set_attribute.assert_any_call(ATTR_NETWORK_PROTOCOL_NAME, "http")

    def test_span_with_tool_name(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            result_span, _, _ = start_span(
                tracer,
                method_name="tools/call",
                protocol_version="2025-06-18",
                server_url="https://example.com",
                tool_name="my_tool",
            )
        assert result_span == span
        tracer.start_span.assert_called_once_with("tools/call my_tool", kind=ANY)
        span.set_attribute.assert_any_call(ATTR_GEN_AI_TOOL_NAME, "my_tool")
        span.set_attribute.assert_any_call(ATTR_GEN_AI_OPERATION_NAME, "execute_tool")

    def test_span_with_network_transport(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            start_span(
                tracer,
                method_name="tools/list",
                protocol_version="2025-06-18",
                server_url="http://example.com",
                network_transport="tcp",
            )
        span.set_attribute.assert_any_call(ATTR_NETWORK_TRANSPORT, "tcp")

    def test_span_tools_call_sets_operation_name(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            start_span(
                tracer,
                method_name="tools/call",
                protocol_version="2025-06-18",
                server_url="http://example.com",
            )
        span.set_attribute.assert_any_call(ATTR_GEN_AI_OPERATION_NAME, "execute_tool")

    def test_non_tools_call_does_not_set_operation_name(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            start_span(
                tracer,
                method_name="tools/list",
                protocol_version="2025-06-18",
                server_url="http://example.com",
            )
        calls = [str(c) for c in span.set_attribute.call_args_list]
        assert not any(ATTR_GEN_AI_OPERATION_NAME in c for c in calls)

    def test_returns_none_tuple_on_exception(self):
        tracer = MagicMock()
        tracer.start_span.side_effect = Exception("tracer failed")
        with self._patch_trace():
            result_span, traceparent, tracestate = start_span(
                tracer,
                method_name="tools/list",
                protocol_version="2025-06-18",
                server_url="http://example.com",
            )
        assert result_span is None
        assert traceparent == ""
        assert tracestate == ""

    def test_no_server_port_when_not_in_url(self):
        tracer, span = self._make_tracer()
        with self._patch_trace():
            start_span(
                tracer,
                method_name="tools/list",
                protocol_version="2025-06-18",
                server_url="http://example.com",
            )
        port_calls = [
            c for c in span.set_attribute.call_args_list if c[0][0] == ATTR_SERVER_PORT
        ]
        assert len(port_calls) == 0


class TestEndSpan:
    def test_does_nothing_with_none_span(self):
        # Should not raise
        end_span(None)

    def test_ends_span_without_error(self):
        mock_span = MagicMock()
        end_span(mock_span)
        mock_span.end.assert_called_once()
        mock_span.set_status.assert_not_called()

    def test_ends_span_with_error(self):
        mock_span = MagicMock()
        error = ValueError("something went wrong")
        with patch.multiple(
            telemetry_module, Status=MagicMock(), StatusCode=MagicMock()
        ):
            end_span(mock_span, error=error)
        mock_span.set_status.assert_called_once()
        mock_span.set_attribute.assert_any_call(ATTR_ERROR_TYPE, "ValueError")
        mock_span.end.assert_called_once()

    def test_ignores_exception_during_end(self):
        mock_span = MagicMock()
        mock_span.end.side_effect = Exception("span end failed")
        # Should not raise
        end_span(mock_span)


class TestRecordErrorFromJsonrpc:
    def test_sets_error_status_and_attribute(self):
        mock_span = MagicMock()
        with patch.multiple(
            telemetry_module, Status=MagicMock(), StatusCode=MagicMock()
        ):
            record_error_from_jsonrpc(
                mock_span, error_code=-32600, error_message="Invalid Request"
            )
        mock_span.set_status.assert_called_once()
        mock_span.set_attribute.assert_called_once_with(
            ATTR_ERROR_TYPE, "jsonrpc.error.-32600"
        )


class TestRecordOperationDuration:
    def test_does_nothing_with_none_histogram(self):
        # Should not raise
        record_operation_duration(
            None, 1.5, "tools/call", "2025-06-18", "http://example.com"
        )

    def test_records_basic_operation(self):
        mock_histogram = MagicMock()
        record_operation_duration(
            mock_histogram,
            0.5,
            "tools/list",
            "2025-06-18",
            "http://example.com",
        )
        mock_histogram.record.assert_called_once()
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_MCP_METHOD_NAME] == "tools/list"
        assert attrs[ATTR_MCP_PROTOCOL_VERSION] == "2025-06-18"
        assert attrs[ATTR_SERVER_ADDRESS] == "example.com"
        assert attrs[ATTR_NETWORK_PROTOCOL_NAME] == "http"

    def test_records_with_server_port(self):
        mock_histogram = MagicMock()
        record_operation_duration(
            mock_histogram,
            0.5,
            "tools/list",
            "2025-06-18",
            "http://example.com:9090",
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_SERVER_PORT] == 9090

    def test_records_with_tool_name_and_tools_call(self):
        mock_histogram = MagicMock()
        record_operation_duration(
            mock_histogram,
            1.0,
            "tools/call",
            "2025-06-18",
            "http://example.com",
            tool_name="my_tool",
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_GEN_AI_TOOL_NAME] == "my_tool"
        assert attrs[ATTR_GEN_AI_OPERATION_NAME] == "execute_tool"

    def test_records_with_network_transport(self):
        mock_histogram = MagicMock()
        record_operation_duration(
            mock_histogram,
            0.3,
            "tools/list",
            "2025-06-18",
            "http://example.com",
            network_transport="tcp",
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_NETWORK_TRANSPORT] == "tcp"

    def test_records_with_error(self):
        mock_histogram = MagicMock()
        error = RuntimeError("call failed")
        record_operation_duration(
            mock_histogram,
            0.8,
            "tools/call",
            "2025-06-18",
            "http://example.com",
            error=error,
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_ERROR_TYPE] == "RuntimeError"

    def test_ignores_exception_during_record(self):
        mock_histogram = MagicMock()
        mock_histogram.record.side_effect = Exception("record failed")
        # Should not raise
        record_operation_duration(
            mock_histogram, 0.5, "tools/list", "2025-06-18", "http://example.com"
        )


class TestRecordSessionDuration:
    def test_does_nothing_with_none_histogram(self):
        # Should not raise
        record_session_duration(None, 10.0, "2025-06-18", "http://example.com")

    def test_records_basic_session(self):
        mock_histogram = MagicMock()
        record_session_duration(mock_histogram, 5.0, "2025-06-18", "http://example.com")
        mock_histogram.record.assert_called_once()
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_MCP_PROTOCOL_VERSION] == "2025-06-18"
        assert attrs[ATTR_SERVER_ADDRESS] == "example.com"
        assert attrs[ATTR_NETWORK_PROTOCOL_NAME] == "http"

    def test_records_with_server_port(self):
        mock_histogram = MagicMock()
        record_session_duration(
            mock_histogram, 5.0, "2025-06-18", "http://example.com:8080"
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_SERVER_PORT] == 8080

    def test_records_with_network_transport(self):
        mock_histogram = MagicMock()
        record_session_duration(
            mock_histogram,
            5.0,
            "2025-06-18",
            "http://example.com",
            network_transport="tcp",
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_NETWORK_TRANSPORT] == "tcp"

    def test_records_with_error(self):
        mock_histogram = MagicMock()
        error = ConnectionError("disconnected")
        record_session_duration(
            mock_histogram, 2.0, "2025-06-18", "http://example.com", error=error
        )
        attrs = mock_histogram.record.call_args[0][1]
        assert attrs[ATTR_ERROR_TYPE] == "ConnectionError"

    def test_ignores_exception_during_record(self):
        mock_histogram = MagicMock()
        mock_histogram.record.side_effect = Exception("record failed")
        # Should not raise
        record_session_duration(mock_histogram, 5.0, "2025-06-18", "http://example.com")
