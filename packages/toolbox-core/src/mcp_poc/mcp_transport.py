from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import httpx

class ITransport(ABC):
    @abstractmethod
    async def tools_list(self, toolset_name: Optional[str] = None) -> Dict:
        pass

    @abstractmethod
    async def tool_invoke(self, tool_name: str, arguments: Dict, headers: Optional[Dict] = None, auth_services: Optional[List[str]] = None) -> Dict:
        pass

    @abstractmethod
    async def close(self):
        pass

class McpHttpTransport(ITransport):
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip('/')
        self._client = httpx.AsyncClient()
        self._request_id = 0

    def _build_json_rpc_payload(self, method: str, params: Dict) -> Dict:
        self._request_id += 1
        return {"jsonrpc": "2.0", "method": method, "params": params, "id": self._request_id}

    def _get_list_endpoint(self, toolset_name: Optional[str] = None) -> str:
        """Constructs the correct API endpoint for listing tools."""
        if toolset_name:
            return f"{self._base_url}/mcp/{toolset_name}"
        return f"{self._base_url}/mcp"

    async def tools_list(self, toolset_name: Optional[str] = None, headers: Optional[Dict] = None) -> Dict:
        """Lists tools from the default endpoint or a specific toolset."""
        endpoint = self._get_list_endpoint(toolset_name)
        payload = self._build_json_rpc_payload("tools/list", {})
        response = await self._client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def tool_invoke(self, tool_name: str, arguments: Dict, headers: Optional[Dict] = None, auth_services: Optional[List[str]] = None) -> Dict:
        """Invokes a tool using the global /mcp endpoint."""
        endpoint = f"{self._base_url}/mcp"
        params = {"name": tool_name, "arguments": arguments}
        if auth_services:
            params["authServices"] = auth_services
        payload = self._build_json_rpc_payload("tools/call", params)
        response = await self._client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()