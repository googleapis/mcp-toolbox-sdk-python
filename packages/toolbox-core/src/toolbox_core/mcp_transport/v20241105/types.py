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

from typing import Any, Generic, Literal, Type, TypeVar

from pydantic import BaseModel, ConfigDict


class RequestParams(BaseModel):
    model_config = ConfigDict(extra="allow")


class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    method: str
    params: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class JSONRPCNotification(BaseModel):
    """A notification which does not expect a response (no ID)."""

    jsonrpc: Literal["2.0"]
    method: str
    params: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    result: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ErrorData(BaseModel):
    code: int
    message: str
    data: Any | None = None
    model_config = ConfigDict(extra="allow")


class JSONRPCError(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str | int
    error: ErrorData
    model_config = ConfigDict(extra="allow")


class BaseMetadata(BaseModel):
    name: str
    model_config = ConfigDict(extra="allow")


class Implementation(BaseMetadata):
    version: str
    model_config = ConfigDict(extra="allow")


class ClientCapabilities(BaseModel):
    model_config = ConfigDict(extra="allow")


class InitializeRequestParams(RequestParams):
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation
    model_config = ConfigDict(extra="allow")


class ServerCapabilities(BaseModel):
    prompts: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class InitializeResult(BaseModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None
    model_config = ConfigDict(extra="allow")


class Tool(BaseMetadata):
    description: str | None = None
    inputSchema: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ListToolsResult(BaseModel):
    tools: list[Tool]
    model_config = ConfigDict(extra="allow")


class TextContent(BaseModel):
    type: Literal["text"]
    text: str
    model_config = ConfigDict(extra="allow")


class CallToolResult(BaseModel):
    content: list[TextContent]
    isError: bool = False
    model_config = ConfigDict(extra="allow")


ResultT = TypeVar("ResultT", bound=BaseModel)


class MCPRequest(BaseModel, Generic[ResultT]):
    method: str
    params: dict[str, Any] | BaseModel | None = None
    model_config = ConfigDict(extra="allow")

    def get_result_model(self) -> Type[ResultT]:
        raise NotImplementedError


class MCPNotification(BaseModel):
    method: str
    params: dict[str, Any] | BaseModel | None = None
    model_config = ConfigDict(extra="allow")


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


class CallToolRequestParams(BaseModel):
    name: str
    arguments: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class CallToolRequest(MCPRequest[CallToolResult]):
    method: Literal["tools/call"] = "tools/call"
    params: CallToolRequestParams

    def get_result_model(self) -> Type[CallToolResult]:
        return CallToolResult
