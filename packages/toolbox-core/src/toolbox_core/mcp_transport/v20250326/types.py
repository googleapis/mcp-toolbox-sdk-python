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

import uuid
from typing import Any, Generic, Literal, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class _BaseMCPModel(BaseModel):
    """Base model with common configuration."""

    model_config = ConfigDict(extra="allow")


class RequestParams(_BaseMCPModel):
    pass


class JSONRPCRequest(_BaseMCPModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str
    params: dict[str, Any] | None = None


class JSONRPCNotification(_BaseMCPModel):
    """A notification which does not expect a response (no ID)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(_BaseMCPModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    result: dict[str, Any]


class ErrorData(_BaseMCPModel):
    code: int
    message: str
    data: Any | None = None


class JSONRPCError(_BaseMCPModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    error: ErrorData


class BaseMetadata(_BaseMCPModel):
    name: str


class Implementation(BaseMetadata):
    version: str


class ClientCapabilities(_BaseMCPModel):
    pass


class InitializeRequestParams(RequestParams):
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class ServerCapabilities(_BaseMCPModel):
    prompts: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None


class InitializeResult(_BaseMCPModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None


class Tool(BaseMetadata):
    description: str | None = None
    inputSchema: dict[str, Any]


class ListToolsResult(_BaseMCPModel):
    tools: list[Tool]


class TextContent(_BaseMCPModel):
    type: Literal["text"]
    text: str


class CallToolResult(_BaseMCPModel):
    content: list[TextContent]
    isError: bool = False


ResultT = TypeVar("ResultT", bound=BaseModel)


class MCPRequest(_BaseMCPModel, Generic[ResultT]):
    method: str
    params: dict[str, Any] | BaseModel | None = None

    def get_result_model(self) -> Type[ResultT]:
        raise NotImplementedError


class MCPNotification(_BaseMCPModel):
    method: str
    params: dict[str, Any] | BaseModel | None = None


class InitializeRequest(MCPRequest[InitializeResult]):
    method: Literal["initialize"] = "initialize"
    params: InitializeRequestParams

    def get_result_model(self) -> Type[InitializeResult]:
        return InitializeResult


class InitializedNotification(MCPNotification):
    method: Literal["notifications/initialized"] = "notifications/initialized"
    params: dict[str, Any] = {}


class ListToolsRequest(MCPRequest[ListToolsResult]):
    method: Literal["tools/list"] = "tools/list"
    params: dict[str, Any] = {}

    def get_result_model(self) -> Type[ListToolsResult]:
        return ListToolsResult


class CallToolRequestParams(_BaseMCPModel):
    name: str
    arguments: dict[str, Any]


class CallToolRequest(MCPRequest[CallToolResult]):
    method: Literal["tools/call"] = "tools/call"
    params: CallToolRequestParams

    def get_result_model(self) -> Type[CallToolResult]:
        return CallToolResult
