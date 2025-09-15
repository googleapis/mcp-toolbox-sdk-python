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
from typing import Annotated, Any, Callable, Mapping, Optional, get_args, get_origin
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from aioresponses import CallbackResult, aioresponses

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


@pytest.fixture
def tool_schema_minimal():
    """A tool with no parameters, no auth."""
    return ToolSchema(
        description="Minimal Test Tool",
        parameters=[],
    )


@pytest.fixture
def tool_schema_requires_auth_X():
    """A tool requiring 'auth_service_X'."""
    return ToolSchema(
        description="Tool Requiring Auth X",
        parameters=[
            ParameterSchema(
                name="auth_param_X",  #
                type="string",
                description="Auth X Token",
                authSources=["auth_service_X"],
            ),
            ParameterSchema(name="data", type="string", description="Some data"),
        ],
    )


@pytest.fixture
def tool_schema_with_param_P():
    """A tool with a specific parameter 'param_P'."""
    return ToolSchema(
        description="Tool with Parameter P",
        parameters=[
            ParameterSchema(name="param_P", type="string", description="Parameter P"),
        ],
    )


# --- Helper Functions for Mocking ---


def mock_tool_load(
    aio_resp: aioresponses,
    tool_name: str,
    tool_schema: ToolSchema,
    base_url: str = TEST_BASE_URL,
    server_version: str = "0.0.0",
    status: int = 200,
    callback: Optional[Callable] = None,
    payload_override: Optional[Callable] = None,
):
    """Mocks the GET /api/tool/{tool_name} endpoint."""
    url = f"{base_url}/api/tool/{tool_name}"
    if payload_override is not None:
        payload = payload_override
    else:
        manifest = ManifestSchema(
            serverVersion=server_version, tools={tool_name: tool_schema}
        )
        payload = manifest.model_dump()
    aio_resp.get(
        url,
        payload=payload,
        status=status,
        callback=callback,
    )


def mock_toolset_load(
    aio_resp: aioresponses,
    toolset_name: str,
    tools_dict: Mapping[str, ToolSchema],
    base_url: str = TEST_BASE_URL,
    server_version: str = "0.0.0",
    status: int = 200,
    callback: Optional[Callable] = None,
):
    """Mocks the GET /api/toolset/{toolset_name} endpoint."""
    # Handle default toolset name (empty string)
    url_path = f"toolset/{toolset_name}" if toolset_name else "toolset/"
    url = f"{base_url}/api/{url_path}"
    manifest = ManifestSchema(serverVersion=server_version, tools=tools_dict)
    aio_resp.get(
        url,
        payload=manifest.model_dump(),
        status=status,
        callback=callback,
    )


def mock_tool_invoke(
    aio_resp: aioresponses,
    tool_name: str,
    base_url: str = TEST_BASE_URL,
    response_payload: Any = {"result": "ok"},
    status: int = 200,
    callback: Optional[Callable] = None,
):
    """Mocks the POST /api/tool/{tool_name}/invoke endpoint."""
    url = f"{base_url}/api/tool/{tool_name}/invoke"
    aio_resp.post(
        url,
        payload=response_payload,
        status=status,
        callback=callback,
    )


@pytest.mark.asyncio
async def test_load_tool_success(aioresponses, test_tool_str):
    """
    Tests successfully loading a tool when the API returns a valid manifest.
    """
    # Mock out responses from server
    TOOL_NAME = "test_tool_1"
    mock_tool_load(aioresponses, TOOL_NAME, test_tool_str)
    mock_tool_invoke(aioresponses, TOOL_NAME)

    async with ToolboxClient(TEST_BASE_URL) as client:
        # Load a Tool
        loaded_tool = await client.load_tool(TOOL_NAME)

        # Assertions
        assert callable(loaded_tool)
        # Assert introspection attributes are set correctly
        assert loaded_tool.__name__ == TOOL_NAME
        expected_description = test_tool_str.description
        assert loaded_tool.__doc__ == expected_description

        # Assert signature inspection, including annotated descriptions
        sig = inspect.signature(loaded_tool)
        actual_params_map = sig.parameters
        expected_params_list = test_tool_str.parameters

        assert len(actual_params_map) == len(expected_params_list)

        for expected_param_schema in expected_params_list:
            param_name = expected_param_schema.name
            assert param_name in actual_params_map
            actual_param = actual_params_map[param_name]
            annotation = actual_param.annotation
            assert get_origin(annotation) is Annotated
            annotation_args = get_args(annotation)
            actual_param_description = annotation_args[1]
            assert actual_param_description == expected_param_schema.description

            if expected_param_schema.required:
                assert actual_param.default is inspect.Parameter.empty
            else:
                assert actual_param.default is None

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
    mock_toolset_load(aioresponses, TOOLSET_NAME, manifest.tools)

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

    mock_tool_load(aioresponses, TOOL_NAME, test_tool_str)
    mock_tool_invoke(
        aioresponses, TOOL_NAME, response_payload={"error": ERROR_MESSAGE}, status=500
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        loaded_tool = await client.load_tool(TOOL_NAME)

        with pytest.raises(Exception, match=ERROR_MESSAGE):
            await loaded_tool(param1="some input")


@pytest.mark.asyncio
async def test_load_tool_not_found_in_manifest(aioresponses, test_tool_str):
    """
    Tests that load_tool raises an Exception when the requested tool name is not
    found in the manifest returned by the server, using existing fixtures.
    """
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_xyz"

    mismatched_manifest_payload = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str}
    ).model_dump()

    mock_tool_load(
        aio_resp=aioresponses,
        tool_name=REQUESTED_TOOL_NAME,
        tool_schema=test_tool_str,
        payload_override=mismatched_manifest_payload,
    )

    async with ToolboxClient(TEST_BASE_URL) as client:
        with pytest.raises(
            ValueError, match=f"Tool '{REQUESTED_TOOL_NAME}' not found!"
        ):
            await client.load_tool(REQUESTED_TOOL_NAME)

    aioresponses.assert_called_once_with(
        f"{TEST_BASE_URL}/api/tool/{REQUESTED_TOOL_NAME}", method="GET", headers={}
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
            assert kwargs["headers"].get("my-auth-service_token") == expected_header
            return CallbackResult(status=200, body="{}")

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

    @pytest.mark.asyncio
    async def test_add_auth_token_getters_missing_fail(self, tool_name, client):
        """
        Tests that adding a missing auth token getter raises ValueError.
        """
        AUTH_SERVICE = "xmy-auth-service"

        tool = await client.load_tool(tool_name)

        with pytest.raises(
            ValueError,
            match=f"Authentication source\(s\) \`{AUTH_SERVICE}\` unused by tool \`{tool_name}\`.",
        ):
            tool.add_auth_token_getters({AUTH_SERVICE: {}})

    @pytest.mark.asyncio
    async def test_constructor_getters_missing_fail(self, tool_name, client):
        """
        Tests that adding a missing auth token getter raises ValueError.
        """
        AUTH_SERVICE = "xmy-auth-service"

        with pytest.raises(
            ValueError,
            match=f"Validation failed for tool '{tool_name}': unused auth tokens: {AUTH_SERVICE}.",
        ):
            await client.load_tool(tool_name, auth_token_getters={AUTH_SERVICE: {}})


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
    async def test_bind_params_success(self, tool_name, client):
        """Tests 'bind_params' with a bound parameter specified."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool = tool.bind_params({"argA": 5})

        assert len(tool.__signature__.parameters) == 1
        assert "argA" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argA" in res

    @pytest.mark.asyncio
    async def test_bind_callable_params_success(self, tool_name, client):
        """Tests 'bind_params' with a bound parameter specified."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool = tool.bind_params({"argA": lambda: 5})

        assert len(tool.__signature__.parameters) == 1
        assert "argA" not in tool.__signature__.parameters

        res = await tool(True)
        assert "argA" in res

    @pytest.mark.asyncio
    async def test_bind_params_fail(self, tool_name, client):
        """Tests 'bind_params' with a bound parameter that doesn't exist."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        with pytest.raises(ValueError) as e:
            tool.bind_params({"argC": lambda: 5})
        assert "unable to bind parameters: no parameter named argC" in str(e.value)

    @pytest.mark.asyncio
    async def test_rebind_params_fail(self, tool_name, client):
        """
        Tests that 'bind_params' fails when attempting to re-bind a
        parameter that has already been bound.
        """
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool_with_bound_param = tool.bind_params({"argA": lambda: 10})

        assert len(tool_with_bound_param.__signature__.parameters) == 1
        assert "argA" not in tool_with_bound_param.__signature__.parameters

        with pytest.raises(ValueError) as e:
            tool_with_bound_param.bind_params({"argA": lambda: 20})

        assert "cannot re-bind parameter: parameter 'argA' is already bound" in str(
            e.value
        )

    @pytest.mark.asyncio
    async def test_bind_params_static_value_success(self, tool_name, client):
        """
        Tests bind_params method with a static value.
        """

        bound_value = "Test value"

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_params({"argB": bound_value})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value}

    @pytest.mark.asyncio
    async def test_bind_params_sync_callable_value_success(self, tool_name, client):
        """
        Tests bind_params method with a sync callable value.
        """

        bound_value_result = True
        bound_sync_callable = Mock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_params({"argB": bound_sync_callable})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value_result}
        bound_sync_callable.assert_called_once()

    @pytest.mark.asyncio
    async def test_bind_params_async_callable_value_success(self, tool_name, client):
        """
        Tests bind_params method with an async callable value.
        """

        bound_value_result = True
        bound_async_callable = AsyncMock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_params({"argB": bound_async_callable})

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value_result}
        bound_async_callable.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bind_param_success(self, tool_name, client):
        """Tests 'bind_param' with a bound parameter specified."""
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool = tool.bind_param("argA", 5)

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

        tool = tool.bind_param("argA", lambda: 5)

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

        with pytest.raises(Exception) as e:
            tool.bind_param("argC", lambda: 5)
        assert "unable to bind parameters: no parameter named argC" in str(e.value)

    @pytest.mark.asyncio
    async def test_rebind_param_fail(self, tool_name, client):
        """
        Tests that 'bind_param' fails when attempting to re-bind a
        parameter that has already been bound.
        """
        tool = await client.load_tool(tool_name)

        assert len(tool.__signature__.parameters) == 2
        assert "argA" in tool.__signature__.parameters

        tool_with_bound_param = tool.bind_param("argA", lambda: 10)

        assert len(tool_with_bound_param.__signature__.parameters) == 1
        assert "argA" not in tool_with_bound_param.__signature__.parameters

        with pytest.raises(ValueError) as e:
            tool_with_bound_param.bind_param("argA", lambda: 20)

        assert "cannot re-bind parameter: parameter 'argA' is already bound" in str(
            e.value
        )

    @pytest.mark.asyncio
    async def test_bind_param_static_value_success(self, tool_name, client):
        """
        Tests bind_param method with a static value.
        """

        bound_value = "Test value"

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_param("argB", bound_value)

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value}

    @pytest.mark.asyncio
    async def test_bind_param_sync_callable_value_success(self, tool_name, client):
        """
        Tests bind_param method with a sync callable value.
        """

        bound_value_result = True
        bound_sync_callable = Mock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_param("argB", bound_sync_callable)

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
        Tests bind_param method with an async callable value.
        """

        bound_value_result = True
        bound_async_callable = AsyncMock(return_value=bound_value_result)

        tool = await client.load_tool(tool_name)
        bound_tool = tool.bind_param("argB", bound_async_callable)

        assert bound_tool is not tool
        assert "argB" not in bound_tool.__signature__.parameters
        assert "argA" in bound_tool.__signature__.parameters

        passed_value_a = 42
        res_payload = await bound_tool(argA=passed_value_a)

        assert res_payload == {"argA": passed_value_a, "argB": bound_value_result}
        bound_async_callable.assert_awaited_once()


class TestUnusedParameterValidation:
    """
    Tests for validation errors related to unused auth tokens or bound
    parameters during tool loading.
    """

    # --- Tests for load_tool ---

    @pytest.mark.asyncio
    async def test_load_tool_with_unused_auth_token_raises_error(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_tool raises ValueError if an unused auth token is provided.
        The tool (tool_schema_minimal) does not declare any authSources.
        """
        tool_name = "minimal_tool_for_unused_auth"
        mock_tool_load(
            aioresponses, tool_name, tool_schema_minimal, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_name}': unused auth tokens: unused_auth_service",
            ):
                await client.load_tool(
                    tool_name,
                    auth_token_getters={"unused_auth_service": lambda: "token"},
                )

    @pytest.mark.asyncio
    async def test_load_tool_with_unused_bound_parameter_raises_error(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_tool raises ValueError if an unused bound parameter is
        provided. The tool (tool_schema_minimal) has no parameters to bind.
        """
        tool_name = "minimal_tool_for_unused_bound"
        mock_tool_load(
            aioresponses, tool_name, tool_schema_minimal, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_name}': unused bound parameters: unused_bound_param",
            ):
                await client.load_tool(
                    tool_name, bound_params={"unused_bound_param": "value"}
                )

    @pytest.mark.asyncio
    async def test_load_tool_with_unused_auth_and_bound_raises_error(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_tool raises ValueError if both unused auth and bound params
        are provided.
        """
        tool_name = "minimal_tool_for_unused_both"
        mock_tool_load(
            aioresponses, tool_name, tool_schema_minimal, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_name}': unused auth tokens: unused_auth_service; unused bound parameters: unused_bound_param",
            ):
                await client.load_tool(
                    tool_name,
                    auth_token_getters={"unused_auth_service": lambda: "token"},
                    bound_params={"unused_bound_param": "value"},
                )

    # --- Tests for load_toolset (strict=True) ---

    @pytest.mark.asyncio
    async def test_load_toolset_strict_one_tool_unused_auth_raises(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_toolset(strict=True) with one tool. If that tool doesn't use
        a provided auth token, it raises an error.
        """
        toolset_name = "strict_set_single_tool_unused_auth"
        tool_A_name = "tool_A_minimal"
        tools_dict = {tool_A_name: tool_schema_minimal}
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_A_name}': unused auth tokens: auth_Y",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={"auth_Y": lambda: "tokenY"},
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_first_tool_fails_auth_raises(
        self, aioresponses, tool_schema_minimal, tool_schema_requires_auth_X
    ):
        """
        Tests load_toolset(strict=True). If the first tool processed doesn't use
        a provided auth token (even if other tokens are used by other tools, or
        itself), it raises an error.
        """
        toolset_name = "strict_set_first_tool_fails_auth"
        tool_minimal_name = "minimal_first"
        tool_auth_X_name = "auth_tool_x_later"

        tools_dict = {
            tool_minimal_name: tool_schema_minimal,
            tool_auth_X_name: tool_schema_requires_auth_X,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_minimal_name}': unused auth tokens: auth_service_X",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={
                        "auth_service_X": lambda: "tokenX",
                    },
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_second_tool_fails_auth_raises(
        self, aioresponses, tool_schema_minimal, tool_schema_requires_auth_X
    ):
        """
        Tests load_toolset(strict=True). If the first tool is fine, but a
        subsequent tool doesn't use a provided auth token, it raises an error.
        """
        toolset_name = "strict_set_second_tool_fails_auth"
        tool_auth_X_name = "auth_tool_x_first"
        tool_minimal_name = "minimal_later"

        tools_dict = {
            tool_auth_X_name: tool_schema_requires_auth_X,
            tool_minimal_name: tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_minimal_name}': unused auth tokens: auth_service_X",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={
                        "auth_service_X": lambda: "tokenX",
                    },
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_one_tool_unused_bound_raises(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_toolset(strict=True) with one tool. If that tool doesn't use
        a provided bound parameter, it raises an error.
        """
        toolset_name = "strict_set_single_tool_unused_bound"
        tool_A_name = "tool_A_minimal_for_bound"
        tools_dict = {tool_A_name: tool_schema_minimal}
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_A_name}': unused bound parameters: param_Q",
            ):
                await client.load_toolset(
                    toolset_name,
                    bound_params={"param_Q": "valueQ"},
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_first_tool_fails_bound_raises(
        self, aioresponses, tool_schema_minimal, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=True). If the first tool processed doesn't use
        a provided bound parameter, it raises an error.
        """
        toolset_name = "strict_set_first_tool_fails_bound"
        tool_minimal_name = "minimal_first_bound"
        tool_param_P_name = "param_p_tool_later"

        tools_dict = {
            tool_minimal_name: tool_schema_minimal,
            tool_param_P_name: tool_schema_with_param_P,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_minimal_name}': unused bound parameters: param_P",
            ):
                await client.load_toolset(
                    toolset_name,
                    bound_params={
                        "param_P": "valueP",
                    },
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_second_tool_fails_bound_raises(
        self, aioresponses, tool_schema_minimal, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=True). If the first tool is fine, but a
        subsequent tool doesn't use a provided bound parameter, it raises an error.
        """
        toolset_name = "strict_set_second_tool_fails_bound"
        tool_param_P_name = "param_p_tool_first"
        tool_minimal_name = "minimal_later"

        tools_dict = {
            tool_param_P_name: tool_schema_with_param_P,
            tool_minimal_name: tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_minimal_name}': unused bound parameters: param_P",
            ):
                await client.load_toolset(
                    toolset_name,
                    bound_params={
                        "param_P": "valueP",
                    },
                    strict=True,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_strict_with_unused_auth_and_bound_raises_error(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_toolset(strict=True) raises ValueError if both unused auth
        and bound params exist for a tool. Uses a single minimal tool in the
        set.
        """
        toolset_name = "strict_set_unused_both_minimal_tool"
        tool_minimal_name = "minimal_for_both_strict"
        tools_dict = {tool_minimal_name: tool_schema_minimal}
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool '{tool_minimal_name}': unused auth tokens: stray_auth; unused bound parameters: stray_param",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={"stray_auth": lambda: "stray_token"},
                    bound_params={"stray_param": "stray_value"},
                    strict=True,
                )

    # --- Tests for load_toolset (strict=False) ---

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_globally_unused_auth_raises_error(
        self, aioresponses, tool_schema_minimal, tool_schema_requires_auth_X
    ):
        """
        Tests load_toolset(strict=False) raises ValueError if an auth token is
        unused by ALL tools.
        """
        toolset_name = "non_strict_globally_unused_auth"
        tools_dict = {
            "auth_tool": tool_schema_requires_auth_X,
            "minimal_tool_in_set": tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for toolset '{toolset_name}': unused auth tokens could not be applied to any tool: globally_unused_auth",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={
                        "auth_service_X": lambda: "tokenX",
                        "globally_unused_auth": lambda: "tokenG",
                    },
                    strict=False,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_globally_unused_bound_raises_error(
        self, aioresponses, tool_schema_minimal, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=False) raises ValueError if a bound param is
        unused by ALL tools.
        """
        toolset_name = "non_strict_globally_unused_bound"
        tools_dict = {
            "param_P_tool_in_set": tool_schema_with_param_P,
            "minimal_tool_in_set_bound": tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for toolset '{toolset_name}': unused bound parameters could not be applied to any tool: globally_unused_param",
            ):
                await client.load_toolset(
                    toolset_name,
                    bound_params={
                        "param_P": "valueP",
                        "globally_unused_param": "valueG",
                    },
                    strict=False,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_globally_unused_auth_and_bound_raises_error(
        self, aioresponses, tool_schema_requires_auth_X, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=False) raises ValueError if globally unused
        auth and bound params exist.
        """
        toolset_name = "non_strict_globally_unused_both"
        tools_dict = {
            "auth_tool_for_both": tool_schema_requires_auth_X,
            "param_P_tool_for_both": tool_schema_with_param_P,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for toolset '{toolset_name}': unused auth tokens could not be applied to any tool: globally_unused_auth; unused bound parameters could not be applied to any tool: globally_unused_param",
            ):
                await client.load_toolset(
                    toolset_name,
                    auth_token_getters={
                        "auth_service_X": lambda: "tokenX",
                        "globally_unused_auth": lambda: "tokenG",
                    },
                    bound_params={
                        "param_P": "valueP",
                        "globally_unused_param": "valueG",
                    },
                    strict=False,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_default_name_globally_unused_auth(
        self, aioresponses, tool_schema_minimal
    ):
        """
        Tests load_toolset(strict=False, name=None) raises ValueError for
        globally unused auth, checking the 'default' toolset name in the error.
        """
        toolset_name = None
        expected_error_toolset_name = "default"
        tools_dict = {"some_minimal_tool": tool_schema_minimal}
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for toolset '{expected_error_toolset_name}': unused auth tokens could not be applied to any tool: globally_unused_auth_default",
            ):
                await client.load_toolset(
                    name=toolset_name,
                    auth_token_getters={
                        "globally_unused_auth_default": lambda: "token"
                    },
                    strict=False,
                )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_partially_used_auth_succeeds(
        self, aioresponses, tool_schema_minimal, tool_schema_requires_auth_X
    ):
        """
        Tests load_toolset(strict=False) succeeds if an auth token is used by at
        least one tool, even if not by all.
        """
        toolset_name = "non_strict_partially_used_auth"
        tools_dict = {
            "auth_tool_partial": tool_schema_requires_auth_X,
            "minimal_tool_partial": tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            await client.load_toolset(
                toolset_name,
                auth_token_getters={"auth_service_X": lambda: "tokenX"},
                strict=False,
            )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_partially_used_bound_succeeds(
        self, aioresponses, tool_schema_minimal, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=False) succeeds if a bound param is used by at
        least one tool, even if not by all.
        """
        toolset_name = "non_strict_partially_used_bound"
        tools_dict = {
            "param_P_tool_partial": tool_schema_with_param_P,
            "minimal_tool_partial_bound": tool_schema_minimal,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            await client.load_toolset(
                toolset_name,
                bound_params={"param_P": "valueP"},
                strict=False,
            )

    @pytest.mark.asyncio
    async def test_load_toolset_non_strict_partially_used_auth_and_bound_succeeds(
        self, aioresponses, tool_schema_requires_auth_X, tool_schema_with_param_P
    ):
        """
        Tests load_toolset(strict=False) succeeds if both an auth token and a
        bound param is used by at least one tool, even if not by all.
        """
        toolset_name = "non_strict_partially_used_both"
        tools_dict = {
            "auth_tool_for_both": tool_schema_requires_auth_X,
            "param_P_tool_for_both": tool_schema_with_param_P,
        }
        mock_toolset_load(
            aioresponses, toolset_name, tools_dict, base_url=TEST_BASE_URL
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            await client.load_toolset(
                toolset_name,
                auth_token_getters={
                    "auth_service_X": lambda: "tokenX",
                },
                bound_params={
                    "param_P": "valueP",
                },
                strict=False,
            )


class TestClientHeaders:
    @pytest.fixture
    def static_header(self):
        return {"X-Static-Header": "static_value"}

    @pytest.fixture
    def sync_callable_header_value(self):
        return "sync_callable_value"

    @pytest.fixture
    def sync_callable_header(self, sync_callable_header_value):
        return {"X-Sync-Callable-Header": Mock(return_value=sync_callable_header_value)}

    @pytest.fixture
    def async_callable_header_value(self):
        return "async_callable_value"

    @pytest.fixture
    def async_callable_header(self, async_callable_header_value):
        return {
            "X-Async-Callable-Header": AsyncMock(
                return_value=async_callable_header_value
            )
        }

    @staticmethod
    def create_callback_factory(
        expected_header,
        callback_payload,
        callback_status: int = 200,
    ) -> Callable:
        """
        Factory that RETURNS a callback function for aioresponses. The returned
        callback will check headers and return the specified payload/status.
        """

        def actual_callback(url, **kwargs):
            received_headers = kwargs.get("headers")
            assert received_headers == expected_header
            return CallbackResult(status=callback_status, payload=callback_payload)

        return actual_callback

    @pytest.mark.asyncio
    async def test_client_init_with_headers(self, static_header):
        """Tests client initialization with static headers."""
        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            assert client._ToolboxClient__client_headers == static_header

    @pytest.mark.asyncio
    async def test_load_tool_with_static_headers(
        self, aioresponses, test_tool_str, static_header
    ):
        """Tests loading and invoking a tool with static client headers."""
        tool_name = "tool_with_static_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok"}

        get_callback = self.create_callback_factory(
            expected_header=static_header,
            callback_payload=manifest.model_dump(),
        )
        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        post_callback = self.create_callback_factory(
            expected_header=static_header,
            callback_payload=expected_payload,
        )
        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
        )

        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            tool = await client.load_tool(tool_name)
            result = await tool(param1="test")
            assert result == expected_payload["result"]

    @pytest.mark.asyncio
    async def test_load_tool_with_sync_callable_headers(
        self,
        aioresponses,
        test_tool_str,
        sync_callable_header,
        sync_callable_header_value,
    ):
        """Tests loading and invoking a tool with sync callable client
        headers."""
        tool_name = "tool_with_sync_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_sync"}
        header_key = list(sync_callable_header.keys())[0]
        header_mock = sync_callable_header[header_key]
        resolved_header = {header_key: sync_callable_header_value}

        get_callback = self.create_callback_factory(
            expected_header=resolved_header,
            callback_payload=manifest.model_dump(),
        )
        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        post_callback = self.create_callback_factory(
            expected_header=resolved_header,
            callback_payload=expected_payload,
        )
        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
        )

        async with ToolboxClient(
            TEST_BASE_URL, client_headers=sync_callable_header
        ) as client:
            tool = await client.load_tool(tool_name)
            header_mock.assert_called_once()  # GET

            header_mock.reset_mock()  # Reset before invoke

            result = await tool(param1="test")
            assert result == expected_payload["result"]
            header_mock.assert_called_once()  # POST/invoke

    @pytest.mark.asyncio
    async def test_load_tool_with_async_callable_headers(
        self,
        aioresponses,
        test_tool_str,
        async_callable_header,
        async_callable_header_value,
    ):
        """Tests loading and invoking a tool with async callable client
        headers."""
        tool_name = "tool_with_async_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_async"}

        header_key = list(async_callable_header.keys())[0]
        header_mock: AsyncMock = async_callable_header[header_key]  # Get the AsyncMock

        # Calculate expected result using the VALUE fixture
        resolved_header = {header_key: async_callable_header_value}

        get_callback = self.create_callback_factory(
            expected_header=resolved_header,
            callback_payload=manifest.model_dump(),
        )
        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        post_callback = self.create_callback_factory(
            expected_header=resolved_header,
            callback_payload=expected_payload,
        )
        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
        )

        async with ToolboxClient(
            TEST_BASE_URL, client_headers=async_callable_header
        ) as client:
            tool = await client.load_tool(tool_name)
            header_mock.assert_awaited_once()  # GET

            header_mock.reset_mock()

            result = await tool(param1="test")
            assert result == expected_payload["result"]
            header_mock.assert_awaited_once()  # POST/invoke

    @pytest.mark.asyncio
    async def test_load_toolset_with_headers(
        self, aioresponses, test_tool_str, static_header
    ):
        """Tests loading a toolset with client headers."""
        toolset_name = "toolset_with_headers"
        tool_name = "tool_in_set"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )

        get_callback = self.create_callback_factory(
            expected_header=static_header,
            callback_payload=manifest.model_dump(),
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/toolset/{toolset_name}", callback=get_callback
        )
        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            tools = await client.load_toolset(toolset_name)
            assert len(tools) == 1
            assert tools[0].__name__ == tool_name

    @pytest.mark.asyncio
    async def test_add_headers_success(
        self, aioresponses, test_tool_str, static_header
    ):
        """Tests adding headers after client initialization."""
        tool_name = "tool_after_add_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "added_ok"}

        get_callback = self.create_callback_factory(
            expected_header=static_header,
            callback_payload=manifest.model_dump(),
        )
        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        post_callback = self.create_callback_factory(
            expected_header=static_header,
            callback_payload=expected_payload,
        )
        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.warns(
                DeprecationWarning,
                match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
            ):
                client.add_headers(static_header)
            assert client._ToolboxClient__client_headers == static_header

            tool = await client.load_tool(tool_name)
            result = await tool(param1="test")
            assert result == expected_payload["result"]

    @pytest.mark.asyncio
    async def test_add_headers_deprecation_warning(self):
        """Tests that add_headers issues a DeprecationWarning."""
        async with ToolboxClient(TEST_BASE_URL) as client:
            with pytest.warns(
                DeprecationWarning,
                match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
            ):
                client.add_headers({"X-Deprecated-Test": "value"})

    @pytest.mark.asyncio
    async def test_add_headers_duplicate_fail(self, static_header):
        """Tests that adding a duplicate header via add_headers raises
        ValueError."""
        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            with pytest.warns(
                DeprecationWarning,
                match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
            ):
                with pytest.raises(
                    ValueError,
                    match=f"Client header\\(s\\) `X-Static-Header` already registered",
                ):
                    client.add_headers(static_header)
