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
import json
from unittest.mock import AsyncMock, Mock

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
        expected_description = (
            test_tool_str.description
            + f"\n\nArgs:\n    param1 (str): Description of Param1"
        )
        assert loaded_tool.__doc__ == expected_description

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


@pytest.mark.asyncio
async def test_invoke_tool_server_error(aioresponses, test_tool_str):
    """Tests that invoking a tool raises an Exception when the server returns an
    error status."""
    TOOL_NAME = "server_error_tool"
    ERROR_MESSAGE = "Simulated Server Error"
    manifest = ManifestSchema(serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str})

    aioresponses.get(
        f"{TEST_BASE_URL}/api/tool/{TOOL_NAME}",
        payload=manifest.model_dump(),
        status=200,
    )
    aioresponses.post(
        f"{TEST_BASE_URL}/api/tool/{TOOL_NAME}/invoke",
        payload={"error": ERROR_MESSAGE},
        status=500,
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        loaded_tool = await client.load_tool(TOOL_NAME)

        with pytest.raises(Exception, match=ERROR_MESSAGE):
            await loaded_tool(param1="some input")


@pytest.mark.asyncio
async def test_load_tool_not_found_in_manifest(aioresponses, test_tool_str):
    """
    Tests that load_tool raises an Exception when the requested tool name
    is not found in the manifest returned by the server, using existing fixtures.
    """
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_xyz"

    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str}
    )

    aioresponses.get(
        f"{TEST_BASE_URL}/api/tool/{REQUESTED_TOOL_NAME}",
        payload=manifest.model_dump(),
        status=200,
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        with pytest.raises(Exception, match=f"Tool '{REQUESTED_TOOL_NAME}' not found!"):
            await client.load_tool(REQUESTED_TOOL_NAME)

    aioresponses.assert_called_once_with(
        f"{TEST_BASE_URL}/api/tool/{REQUESTED_TOOL_NAME}", method="GET"
    )


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
            tool_name, auth_token_getters={"my-auth-service": token_handler}
        )
        await tool(5)

    @pytest.mark.asyncio
    async def test_auth_with_add_token_success(
        self, tool_name, expected_header, client
    ):
        """Tests 'load_tool' with auth token is specified."""

        def token_handler():
            return expected_header

        tool = await client.load_tool(tool_name)
        tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
        await tool(5)

    @pytest.mark.asyncio
    async def test_auth_with_load_tool_fail_no_token(
        self, tool_name, expected_header, client
    ):
        """Tests 'load_tool' with auth token is specified."""

        tool = await client.load_tool(tool_name)
        with pytest.raises(Exception):
            await tool(5)

    @pytest.mark.asyncio
    async def test_add_auth_token_getters_duplicate_fail(self, tool_name, client):
        """
        Tests that adding a duplicate auth token getter raises ValueError.
        """
        AUTH_SERVICE = "my-auth-service"

        tool = await client.load_tool(tool_name)

        authed_tool = tool.add_auth_token_getters({AUTH_SERVICE: {}})
        assert AUTH_SERVICE in authed_tool._ToolboxTool__auth_service_token_getters

        with pytest.raises(
            ValueError,
            match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` already registered in tool `{tool_name}`.",
        ):
            authed_tool.add_auth_token_getters({AUTH_SERVICE: {}})


class TestBoundParameter:

    @pytest.fixture
    def tool_name(self):
        return "tool1"

    @pytest_asyncio.fixture
    async def client(self, aioresponses, test_tool_int_bool, tool_name):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_int_bool}
        )

        # mock toolset GET call
        aioresponses.get(
            f"{TEST_BASE_URL}/api/toolset/",
            payload=manifest.model_dump(),
            status=200,
        )

        # mock tool GET call
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name}",
            payload=manifest.model_dump(),
            status=200,
        )

        # mock tool INVOKE call
        def reflect_parameters(url, **kwargs):
            body = {"result": kwargs["json"]}
            return CallbackResult(status=200, body=json.dumps(body))

        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke",
            payload=manifest.model_dump(),
            callback=reflect_parameters,
            status=200,
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            yield client

    @pytest.mark.asyncio
    async def test_load_tool_success(self, tool_name, client):
        """Tests 'load_tool' with a bound parameter specified."""
        tool = await client.load_tool(tool_name, bound_params={"argA": lambda: 5})

        assert len(tool.__signature__.parameters) == 1
        assert "argA" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argA" in res

    @pytest.mark.asyncio
    async def test_load_toolset_success(self, tool_name, client):
        """Tests 'load_toolset' with a bound parameter specified."""
        tools = await client.load_toolset("", bound_params={"argB": lambda: "hello"})
        tool = tools[0]

        assert len(tool.__signature__.parameters) == 1
        assert "argB" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argB" in res

    @pytest.mark.asyncio
    async def test_bind_param_success(self, tool_name, client):
        """Tests 'bind_param' with a bound parameter specified."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool = tool.bind_parameters({"argA": 5})

        assert len(tool.__signature__.parameters) == 1
        assert "argA" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argA" in res

    @pytest.mark.asyncio
    async def test_bind_callable_param_success(self, tool_name, client):
        """Tests 'bind_param' with a bound parameter specified."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool = tool.bind_parameters({"argA": lambda: 5})

        assert len(tool.__signature__.parameters) == 1
        assert "argA" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argA" in res

    @pytest.mark.asyncio
    async def test_bind_param_fail(self, tool_name, client):
        """Tests 'bind_param' with a bound parameter that doesn't exist."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        with pytest.raises(Exception):
            tool = tool.bind_parameters({"argC": lambda: 5})

    @pytest.mark.asyncio
    async def test_bind_param_static_value_success(self, tool_name, client):
        """
        Tests bind_parameters method with a static value.
        """

        bound_value = "Test value"

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_parameters({"argB": bound_value})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value}

    @pytest.mark.asyncio
    async def test_bind_param_sync_callable_value_success(self, tool_name, client):
        """
        Tests bind_parameters method with a sync callable value.
        """

        bound_value_result = True
        bound_sync_callable = Mock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_parameters({"argB": bound_sync_callable})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value_result}
        bound_sync_callable.assert_called_once()

    @pytest.mark.asyncio
    async def test_bind_param_async_callable_value_success(self, tool_name, client):
        """
        Tests bind_parameters method with an async callable value.
        """

        bound_value_result = True
        bound_async_callable = AsyncMock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_parameters({"argB": bound_async_callable})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value_result}
        bound_async_callable.assert_awaited_once()
