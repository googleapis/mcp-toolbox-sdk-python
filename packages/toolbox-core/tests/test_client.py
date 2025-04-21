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

import aioresponses
import pytest

from typing import Optional, Callable, Mapping, Any
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

# --- Helper Functions for Mocking ---

def mock_tool_load(
    aio_resp: aioresponses,
    tool_name: str,
    tool_schema: ToolSchema,
    base_url: str = TEST_BASE_URL,
    server_version: str = "0.0.0",
    status: int = 200,
    callback: Optional[Callable] = None,
):
    """Mocks the GET /api/tool/{tool_name} endpoint."""
    url = f"{base_url}/api/tool/{tool_name}"
    manifest = ManifestSchema(serverVersion=server_version, tools={tool_name: tool_schema})
    aio_resp.get(
        url,
        payload=manifest.model_dump(),
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
    mock_tool_invoke(aioresponses, TOOL_NAME, response_payload={"error": ERROR_MESSAGE}, status=500)

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

    url = f"{TEST_BASE_URL}/api/tool/{REQUESTED_TOOL_NAME}"
    aioresponses.get(url, payload=manifest.model_dump(),
                     status=200)

    async with ToolboxClient(TEST_BASE_URL) as client:
        with pytest.raises(Exception, match=f"Tool '{REQUESTED_TOOL_NAME}' not found!"):
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

        # Mock GET for tool definition
        def get_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == static_header
            return CallbackResult(status=200, payload=manifest.model_dump())

        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        # Mock POST for invocation
        def post_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == static_header
            return CallbackResult(status=200, payload=expected_payload)

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
        """Tests loading and invoking a tool with sync callable client headers."""
        tool_name = "tool_with_sync_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_sync"}
        header_key = list(sync_callable_header.keys())[0]
        header_mock = sync_callable_header[header_key]
        resolved_header = {header_key: sync_callable_header_value}

        # Mock GET
        def get_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == resolved_header
            return CallbackResult(status=200, payload=manifest.model_dump())

        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        # Mock POST
        def post_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == resolved_header
            return CallbackResult(status=200, payload=expected_payload)

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
        """Tests loading and invoking a tool with async callable client headers."""
        tool_name = "tool_with_async_callable_headers"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str}
        )
        expected_payload = {"result": "ok_async"}

        header_key = list(async_callable_header.keys())[0]
        header_mock: AsyncMock = async_callable_header[header_key]  # Get the AsyncMock

        # Calculate expected result using the VALUE fixture
        resolved_header = {header_key: async_callable_header_value}

        # Mock GET
        def get_callback(url, **kwargs):
            assert kwargs.get("headers") == resolved_header
            return CallbackResult(status=200, payload=manifest.model_dump())

        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        # Mock POST
        def post_callback(url, **kwargs):
            assert kwargs.get("headers") == resolved_header
            return CallbackResult(status=200, payload=expected_payload)

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

        # Mock GET
        def get_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == static_header
            return CallbackResult(status=200, payload=manifest.model_dump())

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

        # Mock GET
        def get_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == static_header
            return CallbackResult(status=200, payload=manifest.model_dump())

        aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

        # Mock POST
        def post_callback(url, **kwargs):
            # Verify headers
            assert kwargs.get("headers") == static_header
            return CallbackResult(status=200, payload=expected_payload)

        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
        )

        async with ToolboxClient(TEST_BASE_URL) as client:
            await client.add_headers(static_header)
            assert client._ToolboxClient__client_headers == static_header

            tool = await client.load_tool(tool_name)
            result = await tool(param1="test")
            assert result == expected_payload["result"]

    @pytest.mark.asyncio
    async def test_add_headers_duplicate_fail(self, static_header):
        """Tests that adding a duplicate header via add_headers raises ValueError."""
        async with ToolboxClient(TEST_BASE_URL, client_headers=static_header) as client:
            with pytest.raises(
                ValueError,
                match=f"Client header\\(s\\) `X-Static-Header` already registered",
            ):
                await client.add_headers(
                    static_header
                )

    @pytest.mark.asyncio
    async def test_client_header_auth_token_conflict_fail(
        self, aioresponses, test_tool_auth
    ):
        """
        Tests that loading a tool fails if a client header conflicts with an auth token name.
        """
        tool_name = "auth_conflict_tool"
        conflict_key = "my-auth-service_token"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_auth}
        )

        conflicting_headers = {conflict_key: "some_value"}
        auth_getters = {"my-auth-service": lambda: "token_val"}

        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name}",
            payload=manifest.model_dump(),
            status=200,
        )

        async with ToolboxClient(
            TEST_BASE_URL, client_headers=conflicting_headers
        ) as client:
            with pytest.raises(
                ValueError,
                match=f"Client header\\(s\\) `{conflict_key}` already registered",
            ):
                await client.load_tool(tool_name, auth_token_getters=auth_getters)
