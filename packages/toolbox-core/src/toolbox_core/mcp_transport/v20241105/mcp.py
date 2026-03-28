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

import time
from typing import Mapping, Optional, TypeVar

from pydantic import BaseModel

from ... import version
from ...protocol import ManifestSchema
from .. import telemetry
from ..transport_base import _McpHttpTransportBase
from . import types

ReceiveResultT = TypeVar("ReceiveResultT", bound=BaseModel)


class McpHttpTransportV20241105(_McpHttpTransportBase):
    """Transport for the MCP v2024-11-05 protocol."""

    async def _send_request(
        self,
        url: str,
        request: types.MCPRequest[ReceiveResultT] | types.MCPNotification,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ReceiveResultT | None:
        """Sends a JSON-RPC request to the MCP server."""
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
            url, json=payload, headers=dict(headers or {})
        ) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} "
                    f"({response.reason}). Server response: {error_text}"
                )

            if response.status == 204 or response.content.at_eof():
                return None

            json_resp = await response.json()

            # Check for JSON-RPC Error
            if "error" in json_resp:
                try:
                    err = types.JSONRPCError.model_validate(json_resp).error
                    raise RuntimeError(
                        f"MCP request failed with code {err.code}: {err.message}"
                    )
                except Exception:
                    raise RuntimeError(f"MCP request failed: {json_resp.get('error')}")

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
        """Initializes the MCP session."""
        meta: Optional[types.MCPMeta] = None

        if self._telemetry_enabled:
            self._session_start_time = time.time()
            operation_start = time.time()
            span, traceparent, tracestate = telemetry.start_span(
                self._tracer,
                "initialize",
                self._protocol_version,
                self._mcp_base_url,
                network_transport="tcp",
            )
            if span is not None:
                meta = types.MCPMeta(
                    traceparent=traceparent or None,
                    tracestate=tracestate or None,
                )

        params = types.InitializeRequestParams(
            protocolVersion=self._protocol_version,
            capabilities=types.ClientCapabilities(),
            clientInfo=types.Implementation(
                name=self._client_name or "toolbox-core-python",
                version=self._client_version or version.__version__,
            ),
            field_meta=meta,
        )

        error: Optional[Exception] = None
        try:
            result = await self._send_request(
                url=self._mcp_base_url,
                request=types.InitializeRequest(params=params),
                headers=headers,
            )

            if result is None:
                raise RuntimeError(
                    "Failed to initialize session: No response from server."
                )

            self._server_version = result.serverInfo.version

            if result.protocolVersion != self._protocol_version:
                raise RuntimeError(
                    f"MCP version mismatch: client does not support server version {result.protocolVersion}"
                )

            if not result.capabilities.tools:
                if self._manage_session:
                    await self.close()
                raise RuntimeError("Server does not support the 'tools' capability.")

            await self._send_request(
                url=self._mcp_base_url,
                request=types.InitializedNotification(),
                headers=headers,
            )
        except Exception as e:
            error = e
            raise
        finally:
            if self._telemetry_enabled:
                # Record operation duration metric
                operation_duration = time.time() - operation_start
                telemetry.record_operation_duration(
                    self._operation_duration_histogram,
                    operation_duration,
                    "initialize",
                    self._protocol_version,
                    self._mcp_base_url,
                    network_transport="tcp",
                    error=error,
                )
                telemetry.end_span(span, error=error)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        await self._ensure_initialized(headers=headers)

        url = self._mcp_base_url + (toolset_name if toolset_name else "")

        meta: Optional[types.MCPMeta] = None

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
                meta = types.MCPMeta(
                    traceparent=traceparent or None,
                    tracestate=tracestate or None,
                )

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

            tools_map = {
                t.name: self._convert_tool_schema(
                    t.model_dump(mode="json", by_alias=True)
                )
                for t in result.tools
            }
            if self._server_version is None:
                raise RuntimeError("Server version not available.")

            return ManifestSchema(serverVersion=self._server_version, tools=tools_map)
        except Exception as e:
            error = e
            raise
        finally:
            if self._telemetry_enabled:
                # Record operation duration metric
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
                # End span
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

    async def close(self):
        """Closes the MCP session and records session duration metric."""
        if self._telemetry_enabled:
            # Record session duration if session was initialized
            if self._session_start_time is not None:
                session_duration = time.time() - self._session_start_time
                telemetry.record_session_duration(
                    self._session_duration_histogram,
                    session_duration,
                    self._protocol_version,
                    self._mcp_base_url,
                    network_transport="tcp",
                )
        # Call parent's close method
        await super().close()

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self._ensure_initialized(headers=headers)

        meta: Optional[types.MCPMeta] = None

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
            if span is not None:
                meta = types.MCPMeta(
                    traceparent=traceparent or None,
                    tracestate=tracestate or None,
                )

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
                # Record operation duration metric
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
                # End span
                telemetry.end_span(span, error=error)
