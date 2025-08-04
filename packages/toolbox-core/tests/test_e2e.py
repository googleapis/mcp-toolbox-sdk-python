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

from inspect import Parameter, signature
from typing import Any, Optional

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

    async def test_load_toolset_default(self, toolbox: ToolboxClient):
        """Load the default toolset, i.e. all tools."""
        toolset = await toolbox.load_toolset()
        assert len(toolset) == 7
        tool_names = {tool.__name__ for tool in toolset}
        expected_tools = [
            "get-row-by-content-auth",
            "get-row-by-email-auth",
            "get-row-by-id-auth",
            "get-row-by-id",
            "get-n-rows",
            "search-rows",
            "process-data",
        ]
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
        new_tool = get_n_rows_tool.bind_params({"num_rows": "3"})
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
        new_tool = get_n_rows_tool.bind_params({"num_rows": lambda: "3"})
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

        with pytest.raises(
            ValueError,
            match=rf"Validation failed for tool 'get-row-by-id': unused auth tokens: my-test-auth",
        ):
            await toolbox.load_tool(
                "get-row-by-id",
                auth_token_getters={"my-test-auth": lambda: auth_token2},
            )

    async def test_run_tool_no_auth(self, toolbox: ToolboxClient):
        """Tests running a tool requiring auth without providing auth."""
        tool = await toolbox.load_tool("get-row-by-id-auth")
        with pytest.raises(
            PermissionError,
            match="One or more of the following authn services are required to invoke this tool: my-test-auth",
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

    @pytest.mark.asyncio
    async def test_run_tool_async_auth(self, toolbox: ToolboxClient, auth_token1: str):
        """Tests running a tool with correct auth using an async token getter."""
        tool = await toolbox.load_tool("get-row-by-id-auth")

        async def get_token_asynchronously():
            return auth_token1

        auth_tool = tool.add_auth_token_getters(
            {"my-test-auth": get_token_asynchronously}
        )
        response = await auth_tool(id="2")
        assert "row2" in response

    async def test_run_tool_param_auth_no_auth(self, toolbox: ToolboxClient):
        """Tests running a tool with a param requiring auth, without auth."""
        tool = await toolbox.load_tool("get-row-by-email-auth")
        with pytest.raises(
            PermissionError,
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


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestOptionalParams:
    """
    End-to-end tests for tools with optional parameters.
    """

    async def test_tool_signature_is_correct(self, toolbox: ToolboxClient):
        """Verify the client correctly constructs the signature for a tool with optional params."""
        tool = await toolbox.load_tool("search-rows")
        sig = signature(tool)

        assert "email" in sig.parameters
        assert "data" in sig.parameters
        assert "id" in sig.parameters

        # The required parameter should have no default
        assert sig.parameters["email"].default is Parameter.empty
        assert sig.parameters["email"].annotation is str

        # The optional parameter should have a default of None
        assert sig.parameters["data"].default is None
        assert sig.parameters["data"].annotation is Optional[str]

        # The optional parameter should have a default of None
        assert sig.parameters["id"].default is None
        assert sig.parameters["id"].annotation is Optional[int]

    async def test_run_tool_with_optional_params_omitted(self, toolbox: ToolboxClient):
        """Invoke a tool providing only the required parameter."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com")
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" in response
        assert "row3" not in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_optional_data_provided(self, toolbox: ToolboxClient):
        """Invoke a tool providing both required and optional parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", data="row3")
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" not in response
        assert "row3" in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_optional_data_null(self, toolbox: ToolboxClient):
        """Invoke a tool providing both required and optional parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", data=None)
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" in response
        assert "row3" not in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_optional_id_provided(self, toolbox: ToolboxClient):
        """Invoke a tool providing both required and optional parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=1)
        assert isinstance(response, str)
        assert response == "null"

    async def test_run_tool_with_optional_id_null(self, toolbox: ToolboxClient):
        """Invoke a tool providing both required and optional parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=None)
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" in response
        assert "row3" not in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_missing_required_param(self, toolbox: ToolboxClient):
        """Invoke a tool without its required parameter."""
        tool = await toolbox.load_tool("search-rows")
        with pytest.raises(TypeError, match="missing a required argument: 'email'"):
            await tool(id=5, data="row5")

    async def test_run_tool_with_required_param_null(self, toolbox: ToolboxClient):
        """Invoke a tool without its required parameter."""
        tool = await toolbox.load_tool("search-rows")
        with pytest.raises(ValidationError, match="email"):
            await tool(email=None, id=5, data="row5")

    async def test_run_tool_with_all_default_params(self, toolbox: ToolboxClient):
        """Invoke a tool providing all parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=0, data="row2")
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" in response
        assert "row3" not in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_all_valid_params(self, toolbox: ToolboxClient):
        """Invoke a tool providing all parameters."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=3, data="row3")
        assert isinstance(response, str)
        assert '"email":"twishabansal@google.com"' in response
        assert "row1" not in response
        assert "row2" not in response
        assert "row3" in response
        assert "row4" not in response
        assert "row5" not in response
        assert "row6" not in response

    async def test_run_tool_with_different_email(self, toolbox: ToolboxClient):
        """Invoke a tool providing all parameters but with a different email."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="anubhavdhawan@google.com", id=3, data="row3")
        assert isinstance(response, str)
        assert response == "null"

    async def test_run_tool_with_different_data(self, toolbox: ToolboxClient):
        """Invoke a tool providing all parameters but with a different data."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=3, data="row4")
        assert isinstance(response, str)
        assert response == "null"

    async def test_run_tool_with_different_id(self, toolbox: ToolboxClient):
        """Invoke a tool providing all parameters but with a different data."""
        tool = await toolbox.load_tool("search-rows")

        response = await tool(email="twishabansal@google.com", id=4, data="row3")
        assert isinstance(response, str)
        assert response == "null"


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestMapParams:
    """
    End-to-end tests for tools with map parameters.
    """

    async def test_tool_signature_with_map_params(self, toolbox: ToolboxClient):
        """Verify the client correctly constructs the signature for a tool with map params."""
        tool = await toolbox.load_tool("process-data")
        sig = signature(tool)

        assert "execution_context" in sig.parameters
        assert sig.parameters["execution_context"].annotation == dict[str, Any]
        assert sig.parameters["execution_context"].default is Parameter.empty

        assert "user_scores" in sig.parameters
        assert sig.parameters["user_scores"].annotation == dict[str, int]
        assert sig.parameters["user_scores"].default is Parameter.empty

        assert "feature_flags" in sig.parameters
        assert sig.parameters["feature_flags"].annotation == Optional[dict[str, bool]]
        assert sig.parameters["feature_flags"].default is None

    async def test_run_tool_with_map_params(self, toolbox: ToolboxClient):
        """Invoke a tool with valid map parameters."""
        tool = await toolbox.load_tool("process-data")

        response = await tool(
            execution_context={"env": "prod", "id": 1234, "user": 1234.5},
            user_scores={"user1": 100, "user2": 200},
            feature_flags={"new_feature": True},
        )
        assert isinstance(response, str)
        assert '"execution_context":{"env":"prod","id":1234,"user":1234.5}' in response
        assert '"user_scores":{"user1":100,"user2":200}' in response
        assert '"feature_flags":{"new_feature":true}' in response

    async def test_run_tool_with_optional_map_param_omitted(
        self, toolbox: ToolboxClient
    ):
        """Invoke a tool without the optional map parameter."""
        tool = await toolbox.load_tool("process-data")

        response = await tool(
            execution_context={"env": "dev"}, user_scores={"user3": 300}
        )
        assert isinstance(response, str)
        assert '"execution_context":{"env":"dev"}' in response
        assert '"user_scores":{"user3":300}' in response
        assert '"feature_flags":null' in response

    async def test_run_tool_with_wrong_map_value_type(self, toolbox: ToolboxClient):
        """Invoke a tool with a map parameter having the wrong value type."""
        tool = await toolbox.load_tool("process-data")

        with pytest.raises(ValidationError):
            await tool(
                execution_context={"env": "staging"},
                user_scores={"user4": "not-an-integer"},
            )
