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
from typing import AsyncGenerator, Callable
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses
from pydantic import ValidationError

from toolbox_core.protocol import ParameterSchema
from toolbox_core.tool import ToolboxTool, create_func_docstring, resolve_value

TEST_BASE_URL = "http://toolbox.example.com"
TEST_TOOL_NAME = "sample_tool"


@pytest.fixture
def sample_tool_params() -> list[ParameterSchema]:
    """Parameters for the sample tool."""
    return [
        ParameterSchema(
            name="message", type="string", description="A message to process"
        ),
        ParameterSchema(name="count", type="integer", description="A number"),
    ]


@pytest.fixture
def sample_tool_auth_params() -> list[ParameterSchema]:
    """Parameters for a sample tool requiring authentication."""
    return [
        ParameterSchema(name="target", type="string", description="Target system"),
        ParameterSchema(
            name="token",
            type="string",
            description="Auth token",
            authSources=["test-auth"],
        ),
    ]


@pytest.fixture
def sample_tool_description() -> str:
    """Description for the sample tool."""
    return "A sample tool that processes a message and a count."


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """Provides an aiohttp ClientSession that is closed after the test."""
    async with ClientSession() as session:
        yield session


# --- Fixtures for Client Headers ---


@pytest.fixture
def static_client_header() -> dict[str, str]:
    return {"X-Client-Static": "client-static-value"}


# --- Fixtures for Auth Getters ---


@pytest.fixture
def auth_token_value() -> str:
    return "auth-token-123"


@pytest.fixture
def auth_getters(auth_token_value) -> dict[str, Callable[[], str]]:
    return {"test-auth": lambda: auth_token_value}


@pytest.fixture
def auth_header_key() -> str:
    return "test-auth_token"


def test_create_func_docstring_one_param_real_schema():
    """
    Tests create_func_docstring with one real ParameterSchema instance.
    """
    description = "This tool does one thing."
    params = [
        ParameterSchema(
            name="input_file", type="string", description="Path to the input file."
        )
    ]

    result_docstring = create_func_docstring(description, params)

    expected_docstring = (
        "This tool does one thing.\n\n"
        "Args:\n"
        "    input_file (str): Path to the input file."
    )

    assert result_docstring == expected_docstring


def test_create_func_docstring_multiple_params_real_schema():
    """
    Tests create_func_docstring with multiple real ParameterSchema instances.
    """
    description = "This tool does multiple things."
    params = [
        ParameterSchema(name="query", type="string", description="The search query."),
        ParameterSchema(
            name="max_results", type="integer", description="Maximum results to return."
        ),
        ParameterSchema(
            name="verbose", type="boolean", description="Enable verbose output."
        ),
    ]

    result_docstring = create_func_docstring(description, params)

    expected_docstring = (
        "This tool does multiple things.\n\n"
        "Args:\n"
        "    query (str): The search query.\n"
        "    max_results (int): Maximum results to return.\n"
        "    verbose (bool): Enable verbose output."
    )

    assert result_docstring == expected_docstring


def test_create_func_docstring_no_description_real_schema():
    """
    Tests create_func_docstring with empty description and one real ParameterSchema.
    """
    description = ""
    params = [
        ParameterSchema(
            name="config_id", type="string", description="The ID of the configuration."
        )
    ]

    result_docstring = create_func_docstring(description, params)

    expected_docstring = (
        "\n\nArgs:\n" "    config_id (str): The ID of the configuration."
    )

    assert result_docstring == expected_docstring
    assert result_docstring.startswith("\n\nArgs:")
    assert "config_id (str): The ID of the configuration." in result_docstring


def test_create_func_docstring_no_params():
    """
    Tests create_func_docstring when the params list is empty.
    """
    description = "This is a tool description."
    params = []

    result_docstring = create_func_docstring(description, params)

    assert result_docstring == description
    assert "\n\nArgs:" not in result_docstring


@pytest.mark.asyncio
async def test_tool_creation_callable_and_run(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
):
    """
    Tests creating a ToolboxTool, checks callability, and simulates a run.
    """
    tool_name = TEST_TOOL_NAME
    base_url = TEST_BASE_URL
    invoke_url = f"{base_url}/api/tool/{tool_name}/invoke"

    input_args = {"message": "hello world", "count": 5}
    expected_payload = input_args.copy()
    mock_server_response_body = {"result": "Processed: hello world (5 times)"}
    expected_tool_result = mock_server_response_body["result"]

    with aioresponses() as m:
        m.post(invoke_url, status=200, payload=mock_server_response_body)

        tool_instance = ToolboxTool(
            session=http_session,
            base_url=base_url,
            name=tool_name,
            description=sample_tool_description,
            params=sample_tool_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters={},
            bound_params={},
            client_headers={},
        )

        assert callable(tool_instance), "ToolboxTool instance should be callable"

        assert "message" in tool_instance.__signature__.parameters
        assert "count" in tool_instance.__signature__.parameters
        assert tool_instance.__signature__.parameters["message"].annotation == str
        assert tool_instance.__signature__.parameters["count"].annotation == int

        actual_result = await tool_instance("hello world", 5)

        assert actual_result == expected_tool_result

        m.assert_called_once_with(
            invoke_url, method="POST", json=expected_payload, headers={}
        )


@pytest.mark.asyncio
async def test_tool_run_with_pydantic_validation_error(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
):
    """
    Tests that calling the tool with incorrect argument types raises an error
    due to Pydantic validation *before* making an HTTP request.
    """
    tool_name = TEST_TOOL_NAME
    base_url = TEST_BASE_URL
    invoke_url = f"{base_url}/api/tool/{tool_name}/invoke"

    with aioresponses() as m:
        m.post(invoke_url, status=200, payload={"result": "Should not be called"})

        tool_instance = ToolboxTool(
            session=http_session,
            base_url=base_url,
            name=tool_name,
            description=sample_tool_description,
            params=sample_tool_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters={},
            bound_params={},
            client_headers={},
        )

        assert callable(tool_instance)

        expected_pattern = r"1 validation error for sample_tool\ncount\n  Input should be a valid integer, unable to parse string as an integer \[\s*type=int_parsing,\s*input_value='not-a-number',\s*input_type=str\s*\]*"
        with pytest.raises(ValidationError, match=expected_pattern):
            await tool_instance(message="hello", count="not-a-number")

        m.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "non_callable_source",
    [
        "a simple string",
        12345,
        True,
        False,
        None,
        [1, "two", 3.0],
        {"key": "value", "number": 100},
        object(),
    ],
    ids=[
        "string",
        "integer",
        "bool_true",
        "bool_false",
        "none",
        "list",
        "dict",
        "object",
    ],
)
async def test_resolve_value_non_callable(non_callable_source):
    """
    Tests resolve_value when the source is not callable.
    """
    resolved = await resolve_value(non_callable_source)

    assert resolved is non_callable_source


@pytest.mark.asyncio
async def test_resolve_value_sync_callable():
    """
    Tests resolve_value with a synchronous callable.
    """
    expected_value = "sync result"
    sync_callable = Mock(return_value=expected_value)

    resolved = await resolve_value(sync_callable)

    sync_callable.assert_called_once()
    assert resolved == expected_value


@pytest.mark.asyncio
async def test_resolve_value_async_callable():
    """
    Tests resolve_value with an asynchronous callable (coroutine function).
    """
    expected_value = "async result"
    async_callable = AsyncMock(return_value=expected_value)

    resolved = await resolve_value(async_callable)

    async_callable.assert_awaited_once()
    assert resolved == expected_value


# --- Tests for ToolboxTool Initialization and Validation ---


def test_tool_init_basic(http_session, sample_tool_params, sample_tool_description):
    """Tests basic tool initialization without headers or auth."""
    tool_instance = ToolboxTool(
        session=http_session,
        base_url=TEST_BASE_URL,
        name=TEST_TOOL_NAME,
        description=sample_tool_description,
        params=sample_tool_params,
        required_authn_params={},
        required_authz_tokens=[],
        auth_service_token_getters={},
        bound_params={},
        client_headers={},
    )
    assert tool_instance.__name__ == TEST_TOOL_NAME
    assert inspect.iscoroutinefunction(tool_instance.__call__)
    assert "message" in tool_instance.__signature__.parameters
    assert "count" in tool_instance.__signature__.parameters

    assert tool_instance._ToolboxTool__client_headers == {}
    assert tool_instance._ToolboxTool__auth_service_token_getters == {}


def test_tool_init_with_client_headers(
    http_session, sample_tool_params, sample_tool_description, static_client_header
):
    """Tests tool initialization *with* client headers."""
    tool_instance = ToolboxTool(
        session=http_session,
        base_url=TEST_BASE_URL,
        name=TEST_TOOL_NAME,
        description=sample_tool_description,
        params=sample_tool_params,
        required_authn_params={},
        required_authz_tokens=[],
        auth_service_token_getters={},
        bound_params={},
        client_headers=static_client_header,
    )
    assert tool_instance._ToolboxTool__client_headers == static_client_header


def test_tool_init_header_auth_conflict(
    http_session,
    sample_tool_auth_params,
    sample_tool_description,
    auth_getters,
    auth_header_key,
):
    """Tests ValueError on init if client header conflicts with auth token."""
    conflicting_client_header = {auth_header_key: "some-client-value"}

    with pytest.raises(
        ValueError, match=f"Client header\\(s\\) `{auth_header_key}` already registered"
    ):
        ToolboxTool(
            session=http_session,
            base_url=TEST_BASE_URL,
            name="auth_conflict_tool",
            description=sample_tool_description,
            params=sample_tool_auth_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters=auth_getters,
            bound_params={},
            client_headers=conflicting_client_header,
        )


def test_tool_add_auth_token_getters_conflict_with_existing_client_header(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
):
    """
    Tests ValueError when add_auth_token_getters introduces an auth service
    whose token name conflicts with an existing client header.
    """
    tool_instance = ToolboxTool(
        session=http_session,
        base_url=TEST_BASE_URL,
        name="tool_with_client_header",
        description=sample_tool_description,
        params=sample_tool_params,
        required_authn_params={},
        required_authz_tokens=[],
        auth_service_token_getters={},
        bound_params={},
        client_headers={
            "X-Shared-Auth-Token_token": "value_from_initial_client_headers"
        },
    )
    new_auth_getters_causing_conflict = {
        "X-Shared-Auth-Token": lambda: "token_value_from_new_getter"
    }
    expected_error_message = (
        f"Client header\\(s\\) `X-Shared-Auth-Token_token` already registered in client. "
        f"Cannot register client the same headers in the client as well as tool."
    )

    with pytest.raises(ValueError, match=expected_error_message):
        tool_instance.add_auth_token_getters(new_auth_getters_causing_conflict)
