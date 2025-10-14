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
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional

from aiohttp import ClientSession

from ..itransport import ITransport
from ..protocol import (
    AdditionalPropertiesSchema,
    ManifestSchema,
    ParameterSchema,
    Protocol,
    ToolSchema,
)


class _McpHttpTransportBase(ITransport, ABC):
    """Base transport for MCP protocols."""

    def __init__(
        self,
        base_url: str,
        session: Optional[ClientSession] = None,
        protocol: Protocol = Protocol.MCP,
    ):
        self._mcp_base_url = base_url + "/mcp/"
        self._protocol_version = protocol.value
        self._server_version: Optional[str] = None

        self._manage_session = session is None
        self._session = session or ClientSession()
        self._init_lock = asyncio.Lock()
        self._init_task: Optional[asyncio.Task] = None

    async def _ensure_initialized(self):
        """Ensures the session is initialized before making requests."""
        async with self._init_lock:
            if self._init_task is None:
                self._init_task = asyncio.create_task(self._initialize_session())
        await self._init_task

    @property
    def base_url(self) -> str:
        return self._mcp_base_url

    def _convert_tool_schema(self, tool_data: dict) -> ToolSchema:
        meta = tool_data.get("_meta", {})
        param_auth = meta.get("toolbox/authParams", {})
        invoke_auth = meta.get("toolbox/authInvoke", [])

        parameters = []
        input_schema = tool_data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for name, schema in properties.items():
            additional_props = schema.get("additionalProperties")
            if isinstance(additional_props, dict):
                additional_props = AdditionalPropertiesSchema(
                    type=additional_props["type"]
                )
            else:
                additional_props = True

            auth_sources = param_auth.get(name)
            parameters.append(
                ParameterSchema(
                    name=name,
                    type=schema["type"],
                    description=schema.get("description", ""),
                    required=name in required,
                    additionalProperties=additional_props,
                )
            )

        return ToolSchema(
            description=tool_data["description"],
            parameters=parameters,
            authRequired=invoke_auth,
        )

    async def _list_tools(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Private helper to fetch the raw tool list from the server."""
        if toolset_name:
            url = self._mcp_base_url + toolset_name
        else:
            url = self._mcp_base_url
        return await self._send_request(
            url=url, method="tools/list", params={}, headers=headers
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
        for tool in result.get("tools", []):
            if tool.get("name") == tool_name:
                tool_def = self._convert_tool_schema(tool)
                break

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found.")

        tool_details = ManifestSchema(
            serverVersion=self._server_version,
            tools={tool_name: tool_def},
        )
        return tool_details

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
        tools = result.get("tools")

        return ManifestSchema(
            serverVersion=self._server_version,
            tools={tool["name"]: self._convert_tool_schema(tool) for tool in tools},
        )

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Optional[Mapping[str, str]]
    ) -> str:
        """Invokes a specific tool on the server using the MCP protocol."""
        await self._ensure_initialized()

        url = self._mcp_base_url
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
        async with self._init_lock:
            if self._init_task:
                try:
                    await self._init_task
                except Exception:
                    # If initialization failed, we can still try to close.
                    pass
        if self._manage_session and self._session and not self._session.closed:
            await self._session.close()

    async def _perform_initialization_and_negotiation(
        self, params: dict, headers: Optional[Mapping[str, str]] = None
    ) -> Any:
        """Performs the common initialization and version negotiation logic."""
        initialize_result = await self._send_request(
            url=self._mcp_base_url, method="initialize", params=params, headers=headers
        )

        server_info = initialize_result.get("serverInfo")
        if not server_info:
            raise RuntimeError("Server info not found in initialize response")

        self._server_version = server_info.get("version")
        if not self._server_version:
            raise RuntimeError("Server version not found in initialize response")

        server_protocol_version = initialize_result.get("protocolVersion")
        if server_protocol_version:
            if server_protocol_version != self._protocol_version:
                raise RuntimeError(
                    "MCP version mismatch: client does not support server version"
                    f" {server_protocol_version}"
                )
        else:
            if self._manage_session:
                await self.close()
            raise RuntimeError("MCP Protocol version not found in initialize response")

        server_capabilities = initialize_result.get("capabilities")
        if not server_capabilities or "tools" not in server_capabilities:
            if self._manage_session:
                await self.close()
            raise RuntimeError("Server does not support the 'tools' capability.")
        return initialize_result

    @abstractmethod
    async def _initialize_session(self):
        """Initializes the MCP session."""
        pass

    @abstractmethod
    async def _send_request(
        self,
        url: str,
        method: str,
        params: dict,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Sends a JSON-RPC request to the MCP server."""
        pass
