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
from toolbox_core.protocol import Protocol


async def main():
    """Harness main execution block.

    NOTE: All non-protocol outputs (logs, traces, errors) must be directed to
    sys.stderr. The test runner captures stdout for protocol messages only,
    printing other content to stdout will pollute the stream and crash the runner.
    """
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

    protocol = Protocol.MCP
    if scenario == "request-metadata":
        protocol = Protocol.MCP_LATEST

    async with ToolboxClient(
        server_url, client_headers=client_headers, protocol=protocol
    ) as client:
        if scenario == "initialize":
            await client.load_toolset()
            print("Client initialization test completed", file=sys.stderr)

        elif scenario == "tools_call":
            add_numbers = await client.load_tool("add_numbers")
            await add_numbers(a=1, b=2)
            print("Invoked add_numbers(a=1, b=2)", file=sys.stderr)

        elif scenario == "request-metadata":
            await client.load_toolset()
            print("Client request-metadata test completed", file=sys.stderr)

        else:
            # Default behavior: load default toolset to trigger standard interactions
            await client.load_toolset()


if __name__ == "__main__":
    import os
    import traceback

    try:
        asyncio.run(main())
    except Exception as e:
        print(
            f"\n=== ERROR FOR SCENARIO: {os.environ.get('MCP_CONFORMANCE_SCENARIO', 'unknown')} ===\n",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
