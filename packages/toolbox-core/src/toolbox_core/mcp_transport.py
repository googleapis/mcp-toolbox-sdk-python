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
from typing import Any, Mapping, Optional

from aiohttp import ClientSession

from . import version
from .itransport import ITransport
from .protocol import ManifestSchema, Protocol, ToolSchema


class McpHttpTransport(ITransport):
    """Transport for the MCP protocol."""

    def __init__(
        self,
        base_url: str,
        session: Optional[ClientSession] = None,
        protocol: Protocol = Protocol.MCP,
    ):
        self.__base_url = base_url
        # Store the version the client proposes initially
        self.__proposed_protocol_version = protocol.value
        self.__protocol_version = protocol.value  # Will be updated after negotiation
        self.__server_version: Optional[str] = None
        self.__session_id: Optional[str] = None

        self.__manage_session = session is None
        self.__session = session or ClientSession()
        self.__mcp_initialized: bool = False

    @property
    def base_url(self) -> str:
        return self.__base_url

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        """Gets a single tool from the server by listing all and filtering."""
        if not self.__mcp_initialized:
            await self._initialize_session()
        manifest = await self.tools_list(headers=headers)
        if tool_name in manifest.tools:
            return ManifestSchema(
                serverVersion=manifest.serverVersion,
                tools={tool_name: manifest.tools[tool_name]},
            )
        else:
            raise ValueError(f"Tool '{tool_name}' not found.")

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        if not self.__mcp_initialized:
            await self._initialize_session()
        if toolset_name:
            url = f"{self.__base_url}/mcp/{toolset_name}"
        else:
            url = f"{self.__base_url}/mcp"

        result = await self._send_request(
            url=url, method="tools/list", params={}, headers=headers
        )
        if self.__server_version is None:
            raise RuntimeError("Server version not available.")

        return ManifestSchema(
            serverVersion=self.__server_version,
            tools={tool["name"]: ToolSchema(**tool) for tool in result["tools"]},
        )

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> dict:
        """Invokes a specific tool on the server using the MCP protocol."""
        if not self.__mcp_initialized:
            await self._initialize_session()
        url = f"{self.__base_url}/mcp/"
        params = {"name": tool_name, "arguments": arguments}
        result = await self._send_request(
            url=url, method="tools/call", params=params, headers=headers
        )
        return result

    async def close(self):
        if self.__manage_session and self.__session and not self.__session.closed:
            await self.__session.close()

    async def _initialize_session(self):
        """Initializes the MCP session."""

        if self.__session is None:
            if self.__manage_session:
                self.__session = ClientSession()
            else:
                # Should be unreachable due to __init__ logic, but safe guard.
                raise RuntimeError("ClientSession not available for initialization.")

        url = f"{self.__base_url}/mcp/"

        # Perform version negotitation
        client_supported_versions = Protocol.get_supported_mcp_versions()

        params = {
            "processId": os.getpid(),
            "clientInfo": {
                "name": "toolbox-python-sdk",
                "version": version.__version__,
            },
            "capabilities": {},
            "protocolVersion": self.__proposed_protocol_version,
        }
        # Send initialize notification
        initialize_result = await self._send_request(
            url=url, method="initialize", params=params
        )

        # Get the session id if the proposed version required it
        if self.__proposed_protocol_version == "2025-03-26":
            self.__session_id = initialize_result.get("Mcp-Session-Id")
            if not self.__session_id:
                if self.__manage_session:
                    await self.close()
                raise RuntimeError(
                    "Server did not return a Mcp-Session-Id during initialization."
                )

        # Perform version negotiation based on server response
        server_protcol_version = initialize_result.get("protocolVersion")
        if server_protcol_version:
            if server_protcol_version not in client_supported_versions:
                if self.__manage_session:
                    await self.close()
                raise RuntimeError(
                    f"MCP version mismatch: client does not support server version {server_protcol_version}"
                )
            # Update the protocol version to the one agreed upon by the server.
            self.__protocol_version = server_protcol_version
        else:
            if self.__manage_session:
                await self.close()
            raise RuntimeError("Server version not found in initialize response")

        self.__server_capabilities = initialize_result.get("capabilities")
        if not self.__server_capabilities or "tools" not in self.__server_capabilities:
            if self.__manage_session:
                await self.close()
            raise RuntimeError("Server does not support the 'tools' capability.")
        await self._send_request(url=url, method="notifications/initialized", params={})

        self.__mcp_initialized = True

    async def _send_request(
        self,
        url: str,
        method: str,
        params: dict,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Sends a JSON-RPC request to the MCP server."""

        request_params = params.copy()
        req_headers = dict(headers or {})

        # Check based on the NEGOTIATED version (self.__protocol_version)
        if (
            self.__protocol_version == "2025-03-26"
            and method != "initialize"
            and self.__session_id
        ):
            request_params["Mcp-Session-Id"] = self.__session_id

        if self.__protocol_version == "2025-06-18":
            req_headers["MCP-Protocol-Version"] = self.__protocol_version

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": request_params,
            "id": request_id,
        }
        async with self.__session.post(
            url, json=payload, headers=req_headers
        ) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} ({response.reason}). Server response: {error_text}"
                )
            json_response = await response.json()
            if "error" in json_response:
                error = json_response["error"]
                if error["code"] == -32000:
                    raise RuntimeError(f"MCP version mismatch: {error['message']}")
                else:
                    raise RuntimeError(
                        f"MCP request failed with code {error['code']}: {error['message']}"
                    )
            return json_response.get("result")
