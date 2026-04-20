# Copyright 2026 Google LLC
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
import os
import sys

from toolbox_core.client import ToolboxClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: client.py <server_url>", file=sys.stderr)
        sys.exit(1)

    server_url = sys.argv[-1]
    # Prevent requests going to /mcp/mcp/
    if server_url.endswith("/mcp"):
        server_url = server_url[:-4]
    elif server_url.endswith("/mcp/"):
        server_url = server_url[:-5]
    scenario = os.environ.get("MCP_CONFORMANCE_SCENARIO", "")
    context_json = os.environ.get("MCP_CONFORMANCE_CONTEXT", "{}")
    context = json.loads(context_json)

    print(f"Running scenario: {scenario}", file=sys.stderr)
    print(f"Server URL: {server_url}", file=sys.stderr)
    print(f"Context: {context_json}", file=sys.stderr)

    client_headers = {"Accept": "application/json, text/event-stream"}

    async with ToolboxClient(server_url, client_headers=client_headers) as client:
        if scenario == "initialize":
            print(
                "Client initialized, loading toolset to trigger tools/list",
                file=sys.stderr,
            )
            try:
                await client.load_toolset()
                print("Client initialization test completed", file=sys.stderr)
            except Exception as e:
                print(f"Failed to load toolset: {e}", file=sys.stderr)

        elif scenario == "tools_call":
            print("Loading tool 'add_numbers'", file=sys.stderr)
            try:
                add_numbers = await client.load_tool("add_numbers")
                print("Invoking add_numbers(a=1, b=2)", file=sys.stderr)
                result = await add_numbers(a=1, b=2)
                print(f"Result: {result}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to call tool: {e}", file=sys.stderr)

        else:
            print(f"Unknown or unsupported scenario: {scenario}", file=sys.stderr)
            # Default behavior: load default toolset
            try:
                await client.load_toolset()
            except Exception as e:
                print(f"Default interaction failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error in client: {e}", file=sys.stderr)
        sys.exit(1)
