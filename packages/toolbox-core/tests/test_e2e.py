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
from pydantic import ValidationError

from toolbox_core.client import ToolboxClient
from toolbox_core.tool import ToolboxTool


# --- Shared Fixtures Defined at Module Level ---
@pytest_asyncio.fixture(scope="function")
async def toolbox():
    """Creates a ToolboxClient instance shared by all tests in this module."""
    toolbox = ToolboxClient("http://localhost:5000")
    try:
        yield toolbox
    finally:
        await toolbox.close()


@pytest_asyncio.fixture(scope="function")
async def get_n_rows_tool(toolbox: ToolboxClient) -> ToolboxTool:
    """Load the 'get-n-rows' tool using the shared toolbox client."""
    tool = await toolbox.load_tool("get-n-rows")
    assert tool.__name__ == "get-n-rows"
    return tool


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestBasicE2E:
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
        """Load a specific toolset"""
        toolset = await toolbox.load_toolset(toolset_name)
        assert len(toolset) == expected_length
        tool_names = {tool.__name__ for tool in toolset}
        assert tool_names == set(expected_tools)

    async def test_run_tool(self, get_n_rows_tool: ToolboxTool):
        """Invoke a tool."""
        response = await get_n_rows_tool(num_rows="2")

        assert isinstance(response, str)
        assert "row1" in response
        assert "row2" in response
        assert "row3" not in response

    async def test_run_tool_missing_params(self, get_n_rows_tool: ToolboxTool):
        """Invoke a tool with missing params."""
        with pytest.raises(TypeError, match="missing a required argument: 'num_rows'"):
            await get_n_rows_tool()

    async def test_run_tool_wrong_param_type(self, get_n_rows_tool: ToolboxTool):
        """Invoke a tool with wrong param type."""
        with pytest.raises(
            ValidationError,
            match=r"num_rows\s+Input should be a valid string\s+\[type=string_type,\s+input_value=2,\s+input_type=int\]",
        ):
            await get_n_rows_tool(num_rows=2)


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestBindParams:
    async def test_bind_params(
        self, toolbox: ToolboxClient, get_n_rows_tool: ToolboxTool
    ):
        """Bind a param to an existing tool."""
        new_tool = get_n_rows_tool.bind_parameters({"num_rows": "3"})
        response = await new_tool()
        assert isinstance(response, str)
        assert "row1" in response
        assert "row2" in response
        assert "row3" in response
        assert "row4" not in response

    async def test_bind_params_callable(
        self, toolbox: ToolboxClient, get_n_rows_tool: ToolboxTool
    ):
        """Bind a callable param to an existing tool."""
        new_tool = get_n_rows_tool.bind_parameters({"num_rows": lambda: "3"})
        response = await new_tool()
        assert isinstance(response, str)
        assert "row1" in response
        assert "row2" in response
        assert "row3" in response
        assert "row4" not in response


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestAuth:
    async def test_run_tool_unauth_with_auth(
        self, toolbox: ToolboxClient, auth_token2: str
    ):
        """Tests running a tool that doesn't require auth, with auth provided."""
        tool = await toolbox.load_tool(
            "get-row-by-id", auth_token_getters={"my-test-auth": lambda: auth_token2}
        )
        response = await tool(id="2")
        assert "row2" in response

    async def test_run_tool_no_auth(self, toolbox: ToolboxClient):
        """Tests running a tool requiring auth without providing auth."""
        tool = await toolbox.load_tool("get-row-by-id-auth")
        with pytest.raises(
            Exception,
            match="tool invocation not authorized. Please make sure your specify correct auth headers",
        ):
            await tool(id="2")

    async def test_run_tool_wrong_auth(self, toolbox: ToolboxClient, auth_token2: str):
        """Tests running a tool with incorrect auth. The tool
        requires a different authentication than the one provided."""
        tool = await toolbox.load_tool("get-row-by-id-auth")
        auth_tool = tool.add_auth_token_getters({"my-test-auth": lambda: auth_token2})
        with pytest.raises(
            Exception,
            match="tool invocation not authorized",
        ):
            await auth_tool(id="2")

    async def test_run_tool_auth(self, toolbox: ToolboxClient, auth_token1: str):
        """Tests running a tool with correct auth."""
        tool = await toolbox.load_tool("get-row-by-id-auth")
        auth_tool = tool.add_auth_token_getters({"my-test-auth": lambda: auth_token1})
        response = await auth_tool(id="2")
        assert "row2" in response

    async def test_run_tool_param_auth_no_auth(self, toolbox: ToolboxClient):
        """Tests running a tool with a param requiring auth, without auth."""
        tool = await toolbox.load_tool("get-row-by-email-auth")
        with pytest.raises(
            Exception,
            match="One or more of the following authn services are required to invoke this tool: my-test-auth",
        ):
            await tool()

    async def test_run_tool_param_auth(self, toolbox: ToolboxClient, auth_token1: str):
        """Tests running a tool with a param requiring auth, with correct auth."""
        tool = await toolbox.load_tool(
            "get-row-by-email-auth",
            auth_token_getters={"my-test-auth": lambda: auth_token1},
        )
        response = await tool()
        assert "row4" in response
        assert "row5" in response
        assert "row6" in response

    async def test_run_tool_param_auth_no_field(
        self, toolbox: ToolboxClient, auth_token1: str
    ):
        """Tests running a tool with a param requiring auth, with insufficient auth."""
        tool = await toolbox.load_tool(
            "get-row-by-content-auth",
            auth_token_getters={"my-test-auth": lambda: auth_token1},
        )
        with pytest.raises(
            Exception,
            match="no field named row_data in claims",
        ):
            await tool()
