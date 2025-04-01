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

from toolbox_core import ToolboxClient
from toolbox_core.protocol import ManifestSchema, ParameterSchema, ToolSchema

TEST_BASE_URL = "http://toolbox.example.com"


@pytest.fixture()
def test_tool_str():
    return ToolSchema(
        description="Test Tool 1 Description",
        parameters=[
            ParameterSchema(
                name="param1", type="string", description="Description of Param1"
            )
        ],
    )


@pytest.fixture()
def test_tool_int_bool():
    """Fixture for the second test tool schema."""
    return ToolSchema(
        description="Test Tool 2 Description",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(name="argB", type="boolean", description="Argument B"),
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
