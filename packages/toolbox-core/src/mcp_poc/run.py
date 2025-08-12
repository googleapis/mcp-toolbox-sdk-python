import asyncio
import json
from mcp_transport import McpHttpTransport
from typing import Optional

class MCPClient:
    """A simple client to interact with an MCP server."""
    def __init__(self, base_url: str):
        self._transport = McpHttpTransport(base_url=base_url)

    async def list_tools(self, toolset_name: Optional[str] = None):
        """Lists tools, either all or from a specific toolset."""
        if toolset_name:
            print(f"--> Attempting to list tools from toolset: '{toolset_name}'...")
        else:
            print("--> Attempting to list all tools...")
        
        response = await self._transport.tools_list(toolset_name=toolset_name)
        return response.get("result", {}).get("tools", [])

    async def invoke_tool(self, tool_name: str, args: dict):
        """Invokes a tool using the global endpoint."""
        print(f"\n--> Attempting to invoke tool: '{tool_name}'...")
        response = await self._transport.tool_invoke(tool_name, args)

        
        return response.get("result", {})

    async def close(self):
        await self._transport.close()


async def main():
    server_url = "http://127.0.0.1:5000"
    client = MCPClient(base_url=server_url)

    try:
        # 1. List all available tools
        all_tools = await client.list_tools()
        print("\n✅ All tools listed successfully:")
        print(json.dumps(all_tools, indent=2))

        # 2. List tools from a specific toolset
        custom_toolset_name = "my-toolset-2"
        custom_tools = await client.list_tools(toolset_name=custom_toolset_name)
        print(f"\n✅ Tools from '{custom_toolset_name}' toolset listed successfully:")
        print(json.dumps(custom_tools, indent=2))

        # 3. Invoke a tool. This correctly uses the global endpoint.
        tool_to_invoke = "get-n-rows"
        arguments = {"num_rows": "2"}
        invocation_result = await client.invoke_tool(tool_to_invoke, arguments)
        
        print("\n✅ Tool invoked successfully:")
        print(json.dumps(invocation_result, indent=2))

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())