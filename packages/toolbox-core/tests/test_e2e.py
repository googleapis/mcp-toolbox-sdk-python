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

import pytest
import pytest_asyncio

from toolbox_core.client import ToolboxClient
from toolbox_core.tool import ToolboxTool


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestE2EClient:
    @pytest_asyncio.fixture(scope="function")
    async def toolbox(self):
        toolbox = ToolboxClient("http://localhost:5000")
        return toolbox

    @pytest_asyncio.fixture(scope="function")
    async def get_n_rows_tool(self, toolbox: ToolboxClient) -> ToolboxTool:
        tool = await toolbox.load_tool("get-n-rows")
        assert tool.__name__ == "get-n-rows"
        return tool

    #### Basic e2e tests
    @pytest.mark.parametrize(
        "toolset_name, expected_length, expected_tools",
        [
            ("my-toolset", 1, ["get-row-by-id"]),
            ("my-toolset-2", 2, ["get-n-rows", "get-row-by-id"]),
        ],
    )
    async def test_load_toolset_specific(
        self,
        toolbox: ToolboxClient,
        toolset_name: str,
        expected_length: int,
        expected_tools: list[str],
    ):
        toolset = await toolbox.load_toolset(toolset_name)
        assert len(toolset) == expected_length
        tool_names = {tool.__name__ for tool in toolset}
        assert tool_names == set(expected_tools)

    async def test_run_tool(self, get_n_rows_tool: ToolboxTool):
        response = await get_n_rows_tool(num_rows="2")

        assert isinstance(response, str)
        assert "row1" in response
        assert "row2" in response
        assert "row3" not in response
