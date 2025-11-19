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
        """Converts a raw MCP tool dictionary into the Toolbox ToolSchema."""
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
            description=tool_data.get("description") or "", parameters=parameters
        )

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
