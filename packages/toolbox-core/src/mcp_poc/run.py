import asyncio
import json
from mcp_transport import McpHttpTransport

class MCPClient:
    """A simple client to interact with an MCP server."""
    def __init__(self, base_url: str):
        self._transport = McpHttpTransport(base_url=base_url)

    async def list_all_tools(self):
        print("--> Attempting to list tools...")
        response = await self._transport.tools_list()
        return response.get("result", {}).get("tools", [])

    async def invoke_a_tool(self, tool_name: str, args: dict):
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
        tools = await client.list_all_tools()
        print("\n✅ Tools listed successfully:")
        print(json.dumps(tools, indent=2))

        # 2. Invoke a specific tool
        tool_to_invoke = "get-n-rows"
        arguments = {"num_rows": "2"}
        invocation_result = await client.invoke_a_tool(tool_to_invoke, arguments)
        
        print("\n✅ Tool invoked successfully:")
        print(json.dumps(invocation_result, indent=2))

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())