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

import time
from typing import Mapping, Optional, TypeVar

from pydantic import BaseModel

from ... import version
from ...exceptions import ProtocolNegotiationError
from ...protocol import ManifestSchema, Protocol, TelemetryAttributes
from .. import telemetry
from ..transport_base import _McpHttpTransportBase
from . import types

ReceiveResultT = TypeVar("ReceiveResultT", bound=BaseModel)


class McpHttpTransportV20260618(_McpHttpTransportBase):
    """Transport for the MCP draft Request-Metadata (v2026-06-18) protocol."""

    async def _send_request(
        self,
        url: str,
        request: types.MCPRequest[ReceiveResultT] | types.MCPNotification,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ReceiveResultT | None:
        """Sends a JSON-RPC request to the MCP server."""
        req_headers = dict(headers or {})
        req_headers["MCP-Protocol-Version"] = self._protocol_version

        # Inject SEP-2243 routing headers
        req_headers["Mcp-Method"] = request.method
        params = getattr(request, "params", None)
        if params is not None:
            if request.method in ("tools/call", "prompts/get"):
                name = getattr(params, "name", None)
                if name is not None:
                    req_headers["Mcp-Name"] = str(name)
            elif request.method == "resources/read":
                uri = getattr(params, "uri", None)
                if uri is not None:
                    req_headers["Mcp-Name"] = str(uri)

        # Dynamically update the _meta protocol version in the parameters model
        if hasattr(request, "params") and request.params is not None:
            if (
                hasattr(request.params, "field_meta")
                and request.params.field_meta is not None
            ):
                request.params.field_meta.protocol_version = self._protocol_version

        params = (
            request.params.model_dump(mode="json", exclude_none=True, by_alias=True)
            if isinstance(request.params, BaseModel)
            else request.params
        )

        rpc_msg: BaseModel
        if isinstance(request, types.MCPNotification):
            rpc_msg = types.JSONRPCNotification(method=request.method, params=params)
        else:
            rpc_msg = types.JSONRPCRequest(method=request.method, params=params)

        payload = rpc_msg.model_dump(mode="json", exclude_none=True)

        async with self._session.post(
            url, json=payload, headers=req_headers
        ) as response:
            if response.status == 400:
                try:
                    json_resp = await response.json()
                    if "error" in json_resp:
                        err_val = json_resp["error"]
                        if isinstance(err_val, dict) and err_val.get("code") == -32004:
                            server_supported = err_val.get("data", {}).get(
                                "supported", []
                            )

                            client_supported = (
                                self._supported_protocols
                                or Protocol.get_supported_mcp_versions()
                            )
                            mutually_supported = [
                                v for v in client_supported if v in server_supported
                            ]

                            if mutually_supported:
                                raise ProtocolNegotiationError(mutually_supported[0])
                            else:
                                raise RuntimeError(
                                    "No mutually supported protocol version. "
                                    f"Client supports: {client_supported}, "
                                    f"Server supports: {server_supported}"
                                )
                        elif (
                            isinstance(err_val, str)
                            and "invalid protocol version" in err_val.lower()
                        ):
                            # Cascading Fallback: Legacy servers throw this string error.
                            # We pick the next version from the user's supported list.
                            client_supported = (
                                self._supported_protocols
                                or Protocol.get_supported_mcp_versions()
                            )
                            try:
                                current_idx = client_supported.index(self._protocol_version)
                                if current_idx + 1 < len(client_supported):
                                    raise ProtocolNegotiationError(client_supported[current_idx + 1])
                                else:
                                    raise RuntimeError(
                                        "Server threw 'invalid protocol version' but no fallback versions "
                                        "remain in the user's supported protocols array."
                                    )
                            except ValueError:
                                # Current version not in list somehow, just fallback to highest stateful
                                raise ProtocolNegotiationError(Protocol.MCP_v20251125)
                except Exception as e:
                    if isinstance(e, (RuntimeError, ProtocolNegotiationError)):
                        raise e

            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    "API request failed with status"
                    f" {response.status} ({response.reason}). Server response:"
                    f" {error_text}"
                )

            if response.status == 204 or response.content.at_eof():
                return None

            json_resp = await response.json()

            # Check for JSON-RPC Error
            if "error" in json_resp:
                err_val = json_resp["error"]
                if isinstance(err_val, dict) and err_val.get("code") == -32004:
                    server_supported = err_val.get("data", {}).get("supported", [])
                    client_supported = (
                        self._supported_protocols
                        or Protocol.get_supported_mcp_versions()
                    )
                    mutually_supported = [
                        v for v in client_supported if v in server_supported
                    ]
                    if mutually_supported:
                        raise ProtocolNegotiationError(mutually_supported[0])
                    else:
                        raise RuntimeError(
                            "No mutually supported protocol version. "
                            f"Client supports: {client_supported}, "
                            f"Server supports: {server_supported}"
                        )
                try:
                    err = types.JSONRPCError.model_validate(json_resp).error
                    raise RuntimeError(
                        f"MCP request failed with code {err.code}: {err.message}"
                    )
                except Exception:
                    # Fallback if the error doesn't match our schema exactly
                    raw_error = json_resp.get("error", {})
                    raise RuntimeError(f"MCP request failed: {raw_error}")

            # Parse Result
            if isinstance(request, types.MCPRequest):
                try:
                    rpc_resp = types.JSONRPCResponse.model_validate(json_resp)
                    return request.get_result_model().model_validate(rpc_resp.result)
                except Exception as e:
                    raise RuntimeError(f"Failed to parse JSON-RPC response: {e}")
            return None

    async def _initialize_session(
        self, headers: Optional[Mapping[str, str]] = None
    ) -> None:
        """No-op for stateless transport since there is no session handshake."""
        pass

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        await self._ensure_initialized(headers=headers)

        url = self._mcp_base_url + (toolset_name if toolset_name else "")

        meta = types.MCPMeta(
            protocol_version=self._protocol_version,
            client_info=types.Implementation(
                name=self._client_name or "toolbox-core-python",
                version=self._client_version or version.__version__,
            ),
            client_capabilities=types.ClientCapabilities(),
        )

        if self._telemetry_enabled:
            operation_start = time.time()
            span, traceparent, tracestate = telemetry.start_span(
                self._tracer,
                "tools/list",
                self._protocol_version,
                url,
                network_transport="tcp",
            )
            if span is not None:
                meta.traceparent = traceparent or None
                meta.tracestate = tracestate or None

        error: Optional[Exception] = None
        try:
            result = await self._send_request(
                url=url,
                request=types.ListToolsRequest(
                    params=types.ListToolsRequestParams(field_meta=meta)
                ),
                headers=headers,
            )
            if result is None:
                raise RuntimeError("Failed to list tools: No response from server.")

            tools_map = {t["name"]: self._convert_tool_schema(t) for t in result.tools}

            return ManifestSchema(
                serverVersion="1.0.0",
                tools=tools_map,
            )
        except Exception as e:
            error = e
            raise
        finally:
            if self._telemetry_enabled:
                operation_duration = time.time() - operation_start
                telemetry.record_operation_duration(
                    self._operation_duration_histogram,
                    operation_duration,
                    "tools/list",
                    self._protocol_version,
                    url,
                    network_transport="tcp",
                    error=error,
                )
                telemetry.end_span(span, error=error)

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        """Gets a single tool from the server by listing all and filtering."""
        manifest = await self.tools_list(headers=headers)

        if tool_name not in manifest.tools:
            raise ValueError(f"Tool '{tool_name}' not found.")

        return ManifestSchema(
            serverVersion=manifest.serverVersion,
            tools={tool_name: manifest.tools[tool_name]},
        )

    async def tool_invoke(
        self,
        tool_name: str,
        arguments: dict,
        headers: Optional[Mapping[str, str]],
        telemetry_attributes: Optional[TelemetryAttributes] = None,
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self._ensure_initialized(headers=headers)

        payload = self._build_telemetry_payload(telemetry_attributes)

        meta = types.MCPMeta(
            protocol_version=self._protocol_version,
            client_info=types.Implementation(
                name=self._client_name or "toolbox-core-python",
                version=self._client_version or version.__version__,
            ),
            client_capabilities=types.ClientCapabilities(),
            telemetry_attributes=payload,
        )

        span = None
        if self._telemetry_enabled:
            operation_start = time.time()
            span, traceparent, tracestate = telemetry.start_span(
                self._tracer,
                "tools/call",
                self._protocol_version,
                self._mcp_base_url,
                tool_name=tool_name,
                network_transport="tcp",
            )
            meta.traceparent = traceparent or None
            meta.tracestate = tracestate or None
            if span is not None and payload:
                for key, value in payload.items():
                    span.set_attribute(key, value)

        error: Optional[Exception] = None
        try:
            result = await self._send_request(
                url=self._mcp_base_url,
                request=types.CallToolRequest(
                    params=types.CallToolRequestParams(
                        name=tool_name, arguments=arguments, field_meta=meta
                    )
                ),
                headers=headers,
            )

            if result is None:
                raise RuntimeError(
                    f"Failed to invoke tool '{tool_name}': No response from server."
                )

            return self._process_tool_result_content(result.content)
        except Exception as e:
            error = e
            raise
        finally:
            if self._telemetry_enabled:
                operation_duration = time.time() - operation_start
                telemetry.record_operation_duration(
                    self._operation_duration_histogram,
                    operation_duration,
                    "tools/call",
                    self._protocol_version,
                    self._mcp_base_url,
                    tool_name=tool_name,
                    network_transport="tcp",
                    error=error,
                )
                telemetry.end_span(span, error=error)
