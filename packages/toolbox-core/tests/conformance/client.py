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
    protocol_version_str = os.environ.get("MCP_CONFORMANCE_PROTOCOL_VERSION", "")

    print(f"Running scenario: {scenario}", file=sys.stderr)
    print(f"Server URL: {server_url}", file=sys.stderr)
    print(f"Context: {context_json}", file=sys.stderr)
    print(f"Protocol Version: {protocol_version_str}", file=sys.stderr)

    protocol = Protocol.MCP_LATEST
    if protocol_version_str == "DRAFT-2026-v1":
        protocol = Protocol.MCP_v20260618

    client_headers = {"Accept": "application/json, text/event-stream"}

    async with ToolboxClient(
        server_url, protocol=protocol, client_headers=client_headers
    ) as client:
        if scenario == "initialize":
            await client.load_toolset()
            print("Client initialization test completed", file=sys.stderr)

        elif scenario == "tools_call":
            add_numbers = await client.load_tool("add_numbers")
            await add_numbers(a=1, b=2)
            print("Invoked add_numbers(a=1, b=2)", file=sys.stderr)

        elif scenario == "stateless":
            # 1. Load toolset (triggers server/discover and tools/list internally)
            await client.load_toolset()
            print("Stateless load_toolset completed", file=sys.stderr)

            # 2. Trigger consistent version check by loading a single tool
            try:
                await client.load_tool("test_tool")
                print("Stateless load_tool completed", file=sys.stderr)
            except Exception:
                # It is fine if the tool doesn't exist (we just want to trigger the call)
                pass

            # 3. Trigger cancellation (HTTP abort) by calling a long-running task and cancelling
            try:
                long_running_tool = await client.load_tool("long_running_task")
                # Cancel it using asyncio.wait_for timeout
                await asyncio.wait_for(long_running_tool(), timeout=0.05)
            except asyncio.TimeoutError:
                print(
                    "Aborted long running task as expected via timeout",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"Long running task threw exception: {e}", file=sys.stderr)

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


