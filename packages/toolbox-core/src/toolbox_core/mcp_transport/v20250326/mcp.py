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

import os
import uuid
from typing import Any, Mapping, Optional, TypeVar

from pydantic import BaseModel

from ... import version
from ...protocol import ManifestSchema
from ..transport_base import _McpHttpTransportBase
from . import types

ReceiveResultT = TypeVar("ReceiveResultT", bound=BaseModel)


class McpHttpTransportV20250326(_McpHttpTransportBase):
    """Transport for the MCP v2025-03-26 protocol."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_id: Optional[str] = None

    async def _send_request(
        self,
        url: str,
        request: types.MCPRequest[ReceiveResultT] | types.MCPNotification,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ReceiveResultT | None:
        """Sends a JSON-RPC request to the MCP server."""
        req_headers = dict(headers or {})

        if isinstance(request.params, BaseModel):
            request_params = request.params.model_dump(mode="json", exclude_none=True)
        else:
            request_params = (request.params or {}).copy()

        if request.method != "initialize" and self._session_id:
            request_params["Mcp-Session-Id"] = self._session_id

        if isinstance(request, types.MCPNotification):
            notification = types.JSONRPCNotification(
                jsonrpc="2.0", method=request.method, params=request_params
            )
            payload = notification.model_dump(mode="json", exclude_none=True)
        else:
            json_req = types.JSONRPCRequest(
                jsonrpc="2.0",
                id=str(uuid.uuid4()),
                method=request.method,
                params=request_params,
            )
            payload = json_req.model_dump(mode="json", exclude_none=True)

        async with self._session.post(
            url, json=payload, headers=req_headers
        ) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    "API request failed with status"
                    f" {response.status} ({response.reason}). Server response:"
                    f" {error_text}"
                )

            if response.status == 204 or response.content.at_eof():
                return None

            json_response = await response.json()

            if "error" in json_response:
                try:
                    error_wrapper = types.JSONRPCError.model_validate(json_response)
                    error_data = error_wrapper.error
                    raise RuntimeError(
                        f"MCP request failed with code {error_data.code}:"
                        f" {error_data.message}"
                    )
                except Exception:
                    # Fallback if the error doesn't match our schema exactly
                    raw_error = json_response.get("error", {})
                    raise RuntimeError(f"MCP request failed: {raw_error}")

            try:
                rpc_response = types.JSONRPCResponse.model_validate(json_response)
                if isinstance(request, types.MCPRequest):
                    return request.get_result_model().model_validate(
                        rpc_response.result
                    )
                return None
            except Exception as e:
                raise RuntimeError(f"Failed to parse JSON-RPC response: {e}")

    async def _initialize_session(self):
        """Initializes the MCP session."""
        client_info = types.Implementation(
            name="toolbox-python-sdk", version=version.__version__
        )
        capabilities = types.ClientCapabilities()

        params = types.InitializeRequestParams(
            protocolVersion=self._protocol_version,
            capabilities=capabilities,
            clientInfo=client_info,
        )
        initialize_request = types.InitializeRequest(params=params)
        initialize_result = await self._send_request(
            url=self._mcp_base_url,
            request=initialize_request,
        )

        self._server_version = initialize_result.serverInfo.version

        if initialize_result.protocolVersion != self._protocol_version:
            raise RuntimeError(
                "MCP version mismatch: client does not support server version"
                f" {initialize_result.protocolVersion}"
            )

        if not initialize_result.capabilities.tools:
            if self._manage_session:
                await self.close()
            raise RuntimeError("Server does not support the 'tools' capability.")

        # Extract session ID from extra fields
        extra = initialize_result.model_extra or {}
        self._session_id = extra.get("Mcp-Session-Id")

        if not self._session_id:
            if self._manage_session:
                await self.close()
            raise RuntimeError(
                "Server did not return a Mcp-Session-Id during initialization."
            )

        await self._send_request(
            url=self._mcp_base_url,
            request=types.InitializedNotification(),
        )

    async def _list_tools(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> types.ListToolsResult:
        """Private helper to fetch the raw tool list from the server."""
        if toolset_name:
            url = self._mcp_base_url + toolset_name
        else:
            url = self._mcp_base_url

        result = await self._send_request(
            url=url,
            request=types.ListToolsRequest(),
            headers=headers,
        )
        if result is None:
            raise RuntimeError("Failed to list tools: No response from server.")
        return result

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        await self._ensure_initialized()
        if self._server_version is None:
            raise RuntimeError("Server version not available.")

        result = await self._list_tools(toolset_name, headers)

        tools_map = {}
        for tool in result.tools:
            tool_dict = tool.model_dump(mode="json", by_alias=True)
            tools_map[tool.name] = self._convert_tool_schema(tool_dict)

        return ManifestSchema(
            serverVersion=self._server_version,
            tools=tools_map,
        )

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        """Gets a single tool from the server by listing all and filtering."""
        await self._ensure_initialized()
        if self._server_version is None:
            raise RuntimeError("Server version not available.")

        result = await self._list_tools(headers=headers)
        tool_def = None
        for tool in result.tools:
            if tool.name == tool_name:
                tool_dict = tool.model_dump(mode="json", by_alias=True)
                tool_def = self._convert_tool_schema(tool_dict)
                break

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found.")

        return ManifestSchema(
            serverVersion=self._server_version,
            tools={tool_name: tool_def},
        )

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self._ensure_initialized()

        url = self._mcp_base_url
        call_tool_request = types.CallToolRequest(
            params=types.CallToolRequestParams(name=tool_name, arguments=arguments)
        )
        result = await self._send_request(
            url=url,
            request=call_tool_request,
            headers=headers,
        )

        if result is None:
            raise RuntimeError(f"Failed to invoke tool '{tool_name}': No response from server.")

        content_str = "".join(
            content.text for content in result.content if content.type == "text"
        )
        return content_str or "null"
