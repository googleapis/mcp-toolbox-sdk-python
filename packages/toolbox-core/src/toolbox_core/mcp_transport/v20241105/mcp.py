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

from typing import Mapping, Optional, TypeVar

from pydantic import BaseModel

from ... import version
from ...protocol import ManifestSchema
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
            request.params.model_dump(mode="json", exclude_none=True)
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

    async def _initialize_session(self):
        """Initializes the MCP session."""
        params = types.InitializeRequestParams(
            protocolVersion=self._protocol_version,
            capabilities=types.ClientCapabilities(),
            clientInfo=types.Implementation(
                name="toolbox-python-sdk", version=version.__version__
            ),
        )

        result = await self._send_request(
            url=self._mcp_base_url, request=types.InitializeRequest(params=params)
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
            url=self._mcp_base_url, request=types.InitializedNotification()
        )

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        await self._ensure_initialized()

        url = self._mcp_base_url + (toolset_name if toolset_name else "")
        result = await self._send_request(
            url=url, request=types.ListToolsRequest(), headers=headers
        )
        if result is None:
            raise RuntimeError("Failed to list tools: No response from server.")

        tools_map = {
            t.name: self._convert_tool_schema(t.model_dump(mode="json", by_alias=True))
            for t in result.tools
        }
        if self._server_version is None:
            raise RuntimeError("Server version not available.")

        return ManifestSchema(serverVersion=self._server_version, tools=tools_map)

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
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self._ensure_initialized()

        result = await self._send_request(
            url=self._mcp_base_url,
            request=types.CallToolRequest(
                params=types.CallToolRequestParams(name=tool_name, arguments=arguments)
            ),
            headers=headers,
        )
        if result is None:
            raise RuntimeError(
                f"Failed to invoke tool '{tool_name}': No response from server."
            )

        return "".join(c.text for c in result.content if c.type == "text") or "null"
