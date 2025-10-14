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

from .. import version
from .base import _McpHttpTransportBase


class McpHttpTransport_v20250326(_McpHttpTransportBase):
    """Transport for the MCP v2025-03-26 protocol."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_id: Optional[str] = None

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

        if method != "initialize" and self._session_id:
            request_params["Mcp-Session-Id"] = self._session_id

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": request_params,
        }

        if not method.startswith("notifications/"):
            payload["id"] = str(uuid.uuid4())

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
                error = json_response["error"]
                raise RuntimeError(
                    f"MCP request failed with code {error['code']}: {error['message']}"
                )
            return json_response.get("result")

    async def _initialize_session(self):
        """Initializes the MCP session."""
        params = {
            "processId": os.getpid(),
            "clientInfo": {
                "name": "toolbox-python-sdk",
                "version": version.__version__,
            },
            "capabilities": {},
            "protocolVersion": self._protocol_version,
        }

        initialize_result = await self._perform_initialization_and_negotiation(params)

        self._session_id = initialize_result.get("Mcp-Session-Id")
        if not self._session_id:
            if self._manage_session:
                await self.close()
            raise RuntimeError(
                "Server did not return a Mcp-Session-Id during initialization."
            )

        await self._send_request(
            url=self._mcp_base_url, method="notifications/initialized", params={}
        )
