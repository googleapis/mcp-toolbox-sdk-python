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
import json
from abc import ABC, abstractmethod
from typing import Mapping, Optional, Union

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
        client_name: Optional[str] = None,
        client_version: Optional[str] = None,
    ):
        self._mcp_base_url = f"{base_url}/mcp/"
        self._protocol_version = protocol.value
        self._server_version: Optional[str] = None

        self._client_name = client_name
        self._client_version = client_version

        self._manage_session = session is None
        self._session = session or ClientSession()
        self._init_lock = asyncio.Lock()
        self._init_task: Optional[asyncio.Task] = None

    async def _ensure_initialized(
        self, headers: Optional[Mapping[str, str]] = None
    ) -> None:
        """Ensures the session is initialized before making requests."""
        async with self._init_lock:
            if self._init_task is None:
                self._init_task = asyncio.create_task(
                    self._initialize_session(headers=headers)
                )
        await self._init_task

    @property
    def base_url(self) -> str:
        return self._mcp_base_url

    def _process_tool_result_content(self, content: list) -> str:
        """Processes the tool result content, handling multiple JSON objects."""
        texts = [c.text for c in content if getattr(c, "type", "") == "text"]

        if len(texts) > 1:
            try:
                # Check if all chunks are valid JSON objects (dictionaries)
                if all(isinstance(json.loads(t), dict) for t in texts):
                    return f"[{','.join(texts)}]"
            except (ValueError, TypeError):
                # Not valid JSON or not objects, fall back to simple concatenation
                pass

        return "".join(texts) or "null"

    def _convert_parameter_schema(
        self, name: str, schema: dict, required_fields: list[str]
    ) -> ParameterSchema:
        """Recursively converts a JSON Schema node to a ParameterSchema."""
        param_type = schema.get("type", "string")
        description = schema.get("description", "")

        items_schema: Optional[ParameterSchema] = None
        if param_type == "array" and "items" in schema:
            items_data = schema["items"]

            # To maintain compatibility with third-party MCP servers, we gracefully
            # skip strict typing if 'items' is a list (tuple validation in JSON
            # Schema Draft 7) rather than a dictionary. Arrays missing the 'items'
            # key entirely are also supported natively as generic lists (list[Any]).
            # See: https://json-schema.org/understanding-json-schema/reference/array#items
            if isinstance(items_data, dict):
                items_schema = self._convert_parameter_schema("", items_data, [])

        additional_properties: Optional[Union[AdditionalPropertiesSchema, bool]] = None
        if param_type == "object":
            add_props = schema.get("additionalProperties")
            if isinstance(add_props, dict) and "type" in add_props:
                additional_properties = AdditionalPropertiesSchema(
                    type=add_props["type"]
                )
            elif isinstance(add_props, bool):
                additional_properties = add_props

        return ParameterSchema(
            name=name,
            type=param_type,
            description=description,
            required=name in required_fields if name else True,
            items=items_schema,
            additionalProperties=additional_properties,
            # Auth is handled by _convert_tool_schema
        )

    def _convert_tool_schema(self, tool_data: dict) -> ToolSchema:
        """
        Safely converts the raw tool dictionary from the server into a ToolSchema object,
        robustly handling optional authentication metadata.
        """
        param_auth = None
        invoke_auth = []

        if "_meta" in tool_data and isinstance(tool_data["_meta"], dict):
            meta = tool_data["_meta"]
            if "toolbox/authParam" in meta and isinstance(
                meta["toolbox/authParam"], dict
            ):
                param_auth = meta["toolbox/authParam"]
            if "toolbox/authInvoke" in meta and isinstance(
                meta["toolbox/authInvoke"], list
            ):
                invoke_auth = meta["toolbox/authInvoke"]

        parameters = []
        input_schema = tool_data.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for name, schema in properties.items():
            param_schema = self._convert_parameter_schema(name, schema, required)

            if param_auth and name in param_auth:
                param_schema.authSources = param_auth[name]

            parameters.append(param_schema)

        return ToolSchema(
            description=tool_data.get("description") or "",
            parameters=parameters,
            authRequired=invoke_auth,
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
    async def _initialize_session(
        self, headers: Optional[Mapping[str, str]] = None
    ) -> None:
        """Initializes the MCP session."""
        pass
