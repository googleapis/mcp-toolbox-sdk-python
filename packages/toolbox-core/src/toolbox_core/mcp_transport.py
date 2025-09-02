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
import os
import uuid
from typing import Any, Mapping, Optional, Union

from aiohttp import ClientSession

from . import version
from .itransport import ITransport
from .protocol import (
    AdditionalPropertiesSchema,
    ManifestSchema,
    ParameterSchema,
    Protocol,
    ToolSchema,
)


class McpHttpTransport(ITransport):
    """Transport for the MCP protocol."""

    def __init__(
        self,
        base_url: str,
        session: Optional[ClientSession] = None,
        protocol: Protocol = Protocol.MCP,
    ):
        self.__base_url = base_url
        # Will be updated after negotiation
        self.__protocol_version = protocol.value
        self.__server_version: Optional[str] = None
        self.__session_id: Optional[str] = None

        self.__manage_session = session is None
        self.__session = session or ClientSession()
        self.__init_task = asyncio.create_task(self._initialize_session())

    @property
    def base_url(self) -> str:
        return self.__base_url

    def _convert_tool_schema(self, tool_data: dict) -> ToolSchema:
        parameters = []
        input_schema = tool_data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for name, schema in properties.items():
            additional_props_value = schema.get("additionalProperties")
            final_additional_properties: Union[bool, AdditionalPropertiesSchema] = True

            if isinstance(additional_props_value, dict):
                final_additional_properties = AdditionalPropertiesSchema(
                    type=additional_props_value["type"]
                )
            parameters.append(
                ParameterSchema(
                    name=name,
                    type=schema["type"],
                    description=schema.get("description", ""),
                    required=name in required,
                    additionalProperties=final_additional_properties,
                )
            )

        return ToolSchema(description=tool_data["description"], parameters=parameters)

    async def _list_tools(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Private helper to fetch the raw tool list from the server."""
        if toolset_name:
            url = f"{self.__base_url}/mcp/{toolset_name}"
        else:
            url = f"{self.__base_url}/mcp/"
        return await self._send_request(
            url=url, method="tools/list", params={}, headers=headers
        )

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        """Gets a single tool from the server by listing all and filtering."""
        await self.__init_task

        if self.__server_version is None:
            raise RuntimeError("Server version not available.")

        result = await self._list_tools(headers=headers)
        tool_def = None
        for tool in result.get("tools", []):
            if tool.get("name") == tool_name:
                tool_def = self._convert_tool_schema(tool)
                break

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found.")

        tool_details = ManifestSchema(
            serverVersion=self.__server_version,
            tools={tool_name: tool_def},
        )
        return tool_details

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server using the MCP protocol."""
        await self.__init_task

        if self.__server_version is None:
            raise RuntimeError("Server version not available.")

        result = await self._list_tools(toolset_name, headers)
        tools = result.get("tools")

        return ManifestSchema(
            serverVersion=self.__server_version,
            tools={tool["name"]: self._convert_tool_schema(tool) for tool in tools},
        )

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self.__init_task

        url = f"{self.__base_url}/mcp/"
        params = {"name": tool_name, "arguments": arguments}
        result = await self._send_request(
            url=url, method="tools/call", params=params, headers=headers
        )
        all_content = result.get("content", result)
        content_str = "".join(
            content.get("text", "")
            for content in all_content
            if isinstance(content, dict)
        )
        return content_str or "null"

    async def close(self):
        try:
            await self.__init_task
        except Exception:
            # If initialization failed, we can still try to close the session.
            pass
        finally:
            if self.__manage_session and self.__session and not self.__session.closed:
                await self.__session.close()

    async def _initialize_session(self):
        """Initializes the MCP session."""
        if self.__session is None and self.__manage_session:
            self.__session = ClientSession()

        url = f"{self.__base_url}/mcp/"

        # Perform version negotitation
        client_supported_versions = Protocol.get_supported_mcp_versions()
        proposed_protocol_version = self.__protocol_version
        params = {
            "processId": os.getpid(),
            "clientInfo": {
                "name": "toolbox-python-sdk",
                "version": version.__version__,
            },
            "capabilities": {},
            "protocolVersion": proposed_protocol_version,
        }
        # Send initialize notification
        initialize_result = await self._send_request(
            url=url, method="initialize", params=params
        )

        # Get the session id if the proposed version requires it
        if proposed_protocol_version == "2025-03-26":
            self.__session_id = initialize_result.get("Mcp-Session-Id")
            if not self.__session_id:
                if self.__manage_session:
                    await self.close()
                raise RuntimeError(
                    "Server did not return a Mcp-Session-Id during initialization."
                )
        server_info = initialize_result.get("serverInfo")
        if not server_info:
            raise RuntimeError("Server info not found in initialize response")

        self.__server_version = server_info.get("version")
        if not self.__server_version:
            raise RuntimeError("Server version not found in initialize response")

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
            raise RuntimeError("MCP Protocol version not found in initialize response")

        server_capabilities = initialize_result.get("capabilities")
        if not server_capabilities or "tools" not in server_capabilities:
            if self.__manage_session:
                await self.close()
            raise RuntimeError("Server does not support the 'tools' capability.")
        await self._send_request(url=url, method="notifications/initialized", params={})

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

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": request_params,
        }

        if not method.startswith("notifications/"):
            payload["id"] = str(uuid.uuid4())

        async with self.__session.post(
            url, json=payload, headers=req_headers
        ) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} ({response.reason}). Server response: {error_text}"
                )

            # Handle potential empty body (e.g. 204 No Content for notifications)
            if response.status == 204 or response.content.at_eof():
                return None

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
