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


import inspect

import pytest
import pytest_asyncio
from aioresponses import CallbackResult

from toolbox_core import ToolboxClient
from toolbox_core.protocol import ManifestSchema, ParameterSchema, ToolSchema

TEST_BASE_URL = "http://toolbox.example.com"


@pytest.fixture()
def test_tool_str():
    return ToolSchema(
        description="Test Tool with String input",
        parameters=[
            ParameterSchema(
                name="param1", type="string", description="Description of Param1"
            )
        ],
    )


@pytest.fixture()
def test_tool_int_bool():
    return ToolSchema(
        description="Test Tool with Int, Bool",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(name="argB", type="boolean", description="Argument B"),
        ],
    )


@pytest.fixture()
def test_tool_auth():
    return ToolSchema(
        description="Test Tool with Int,Bool+Auth",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(
                name="argB",
                type="boolean",
                description="Argument B",
                authSources=["my-auth-service"],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_load_tool_success(aioresponses, test_tool_str):
    """
    Tests successfully loading a tool when the API returns a valid manifest.
    """
    # Mock out responses from server
    TOOL_NAME = "test_tool_1"
    manifest = ManifestSchema(serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str})
    aioresponses.get(
        f"{TEST_BASE_URL}/api/tool/{TOOL_NAME}",
        payload=manifest.model_dump(),
        status=200,
    )
    aioresponses.post(
        f"{TEST_BASE_URL}/api/tool/{TOOL_NAME}/invoke",
        payload={"result": "ok"},
        status=200,
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        # Load a Tool
        loaded_tool = await client.load_tool(TOOL_NAME)

        # Assertions
        assert callable(loaded_tool)
        # Assert introspection attributes are set correctly
        assert loaded_tool.__name__ == TOOL_NAME
        assert loaded_tool.__doc__ == test_tool_str.description

        # Assert signature inspection
        sig = inspect.signature(loaded_tool)
        assert list(sig.parameters.keys()) == [p.name for p in test_tool_str.parameters]

        assert await loaded_tool("some value") == "ok"


class TestAuth:

    @pytest.fixture
    def expected_header(self):
        return "some_token_for_testing"

    @pytest.fixture
    def tool_name(self):
        return "tool1"

    @pytest_asyncio.fixture
    async def client(self, aioresponses, test_tool_auth, tool_name, expected_header):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_auth}
        )

        # mock tool GET call
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name}",
            payload=manifest.model_dump(),
            status=200,
        )

        # mock tool INVOKE call
        def require_headers(url, **kwargs):
            if kwargs["headers"].get("my-auth-service_token") == expected_header:
                return CallbackResult(status=200, body="{}")
            else:
                return CallbackResult(status=400, body="{}")

        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke",
            payload=manifest.model_dump(),
            callback=require_headers,
            status=200,
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            yield client

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_success(
        self, tool_name, expected_header, client
    ):
        """Tests 'load_tool' with auth token is specified."""

        def token_handler():
            return expected_header

        tool = await client.load_tool(
            tool_name, auth_service_tokens={"my-auth-service": token_handler}
        )
        res = await tool(5)

    @pytest.mark.asyncio
    async def test_auth_with_add_token_success(
        self, tool_name, expected_header, client
    ):
        """Tests 'load_tool' with auth token is specified."""

        def token_handler():
            return expected_header

        tool = await client.load_tool(tool_name)
        tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
        res = await tool(5)

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_fail_no_token(
        self, tool_name, expected_header, client
    ):
        """Tests 'load_tool' with auth token is specified."""

        def token_handler():
            return expected_header

        tool = await client.load_tool(tool_name)
        with pytest.raises(Exception):
            res = await tool(5)


@pytest.mark.asyncio
async def test_load_toolset_success(aioresponses, test_tool_str, test_tool_int_bool):
    """Tests successfully loading a toolset with multiple tools."""
    TOOLSET_NAME = "my_toolset"
    TOOL1 = "tool1"
    TOOL2 = "tool2"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL1: test_tool_str, TOOL2: test_tool_int_bool}
    )
    aioresponses.get(
        f"{TEST_BASE_URL}/api/toolset/{TOOLSET_NAME}",
        payload=manifest.model_dump(),
        status=200,
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        tools = await client.load_toolset(TOOLSET_NAME)

        assert isinstance(tools, list)
        assert len(tools) == len(manifest.tools)

        # Check if tools were created correctly
        assert {t.__name__ for t in tools} == manifest.tools.keys()
