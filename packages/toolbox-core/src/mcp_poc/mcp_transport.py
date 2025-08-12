from abc import ABC, abstractmethod
from typing import Dict
import httpx

class ITransport(ABC):
    @abstractmethod
    async def tools_list(self) -> Dict:
        pass

    @abstractmethod
    async def tool_invoke(self, tool_name: str, arguments: Dict) -> Dict:
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

    async def tools_list(self) -> Dict:
        payload = self._build_json_rpc_payload("tools/list", {})
        response = await self._client.post(f"{self._base_url}/mcp", json=payload)
        response.raise_for_status()
        return response.json()

    async def tool_invoke(self, tool_name: str, arguments: Dict) -> Dict:
        params = {"name": tool_name, "arguments": arguments}
        payload = self._build_json_rpc_payload("tools/call", params)
        response = await self._client.post(f"{self._base_url}/mcp", json=payload)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()