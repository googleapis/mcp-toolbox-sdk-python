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
from types import MappingProxyType
from typing import AsyncGenerator, Callable, Mapping
from unittest.mock import AsyncMock, Mock
from warnings import catch_warnings, simplefilter

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses
from pydantic import ValidationError

from toolbox_core.protocol import ParameterSchema
from toolbox_core.tool import ToolboxTool, create_func_docstring, resolve_value

TEST_BASE_URL = "http://toolbox.example.com"
HTTPS_BASE_URL = "https://toolbox.example.com"
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


@pytest.fixture
def unused_auth_getters() -> dict[str, Callable[[], str]]:
    """Provides an auth getter for a service not required by sample_tool."""
    return {"unused-auth-service": lambda: "unused-token-value"}


@pytest.fixture
def toolbox_tool(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
) -> ToolboxTool:
    """Fixture for a ToolboxTool instance with common test setup."""
    return ToolboxTool(
        session=http_session,
        base_url=TEST_BASE_URL,
        name=TEST_TOOL_NAME,
        description=sample_tool_description,
        params=sample_tool_params,
        required_authn_params={"message": ["service_a"]},
        required_authz_tokens=["service_b"],
        auth_service_token_getters={"service_x": lambda: "token_x"},
        bound_params={"fixed_param": "fixed_value"},
        client_headers={"X-Test-Client": "client_header_value"},
    )


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
    base_url = HTTPS_BASE_URL
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
    base_url = HTTPS_BASE_URL
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
    with catch_warnings(record=True) as record:
        simplefilter("always")

        tool_instance = ToolboxTool(
            session=http_session,
            base_url=HTTPS_BASE_URL,
            name=TEST_TOOL_NAME,
            description=sample_tool_description,
            params=sample_tool_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters={},
            bound_params={},
            client_headers={},
        )
    assert (
        len(record) == 0
    ), f"ToolboxTool instantiation unexpectedly warned: {[f'{w.category.__name__}: {w.message}' for w in record]}"

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
        base_url=HTTPS_BASE_URL,
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
        base_url=HTTPS_BASE_URL,
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


@pytest.mark.asyncio
async def test_auth_token_overrides_client_header(
    http_session: ClientSession,
    sample_tool_description: str,
    sample_tool_params: list[ParameterSchema],
):
    """
    Tests that an auth token getter's value overrides a client header
    with the same name during the actual tool call.
    """

    auth_service_name = "test-auth"
    auth_header_key = f"{auth_service_name}_token"
    auth_token_value = "value-from-auth-getter-123"
    auth_getters = {auth_service_name: lambda: auth_token_value}

    tool_name = TEST_TOOL_NAME
    base_url = HTTPS_BASE_URL
    invoke_url = f"{base_url}/api/tool/{tool_name}/invoke"

    client_headers = {
        auth_header_key: "value-from-client",
        "X-Another-Header": "another-value",
    }

    input_args = {"message": "test", "count": 1}
    mock_server_response = {"result": "Success"}

    with aioresponses() as m:
        m.post(invoke_url, status=200, payload=mock_server_response)

        tool_instance = ToolboxTool(
            session=http_session,
            base_url=base_url,
            name=tool_name,
            description=sample_tool_description,
            params=sample_tool_params,
            auth_service_token_getters=auth_getters,
            client_headers=client_headers,
            required_authn_params={},
            required_authz_tokens=[],
            bound_params={},
        )

        # Call the tool
        await tool_instance(**input_args)

        m.assert_called_once_with(
            invoke_url,
            method="POST",
            json=input_args,
            headers={
                auth_header_key: auth_token_value,
                "X-Another-Header": "another-value",
            },
        )


def test_add_auth_token_getter_unused_token(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
    unused_auth_getters: Mapping[str, Callable[[], str]],
):
    """
    Tests ValueError when add_auth_token_getters is called with a getter for
    an unused authentication service.
    """
    tool_instance = ToolboxTool(
        session=http_session,
        base_url=HTTPS_BASE_URL,
        name=TEST_TOOL_NAME,
        description=sample_tool_description,
        params=sample_tool_params,
        required_authn_params={},
        required_authz_tokens=[],
        auth_service_token_getters={},
        bound_params={},
        client_headers={},
    )

    expected_error_message = "Authentication source\(s\) \`unused-auth-service\` unused by tool \`sample_tool\`."

    with pytest.raises(ValueError, match=expected_error_message):
        tool_instance.add_auth_token_getter(
            next(iter(unused_auth_getters)),
            unused_auth_getters[next(iter(unused_auth_getters))],
        )


def test_toolbox_tool_underscore_name_property(toolbox_tool: ToolboxTool):
    """Tests the _name property."""
    assert toolbox_tool._name == TEST_TOOL_NAME


def test_toolbox_tool_underscore_description_property(toolbox_tool: ToolboxTool):
    """Tests the _description property."""
    assert (
        toolbox_tool._description
        == "A sample tool that processes a message and a count."
    )


def test_toolbox_tool_underscore_params_property(
    toolbox_tool: ToolboxTool, sample_tool_params: list[ParameterSchema]
):
    """Tests the _params property returns a deep copy."""
    params_copy = toolbox_tool._params
    assert params_copy == sample_tool_params
    assert (
        params_copy is not toolbox_tool._ToolboxTool__params
    )  # Ensure it's a deepcopy
    # Verify modifying the copy does not affect the original
    params_copy.append(
        ParameterSchema(name="new_param", type="integer", description="A new parameter")
    )
    assert (
        len(toolbox_tool._ToolboxTool__params) == 2
    )  # Original should remain unchanged


def test_toolbox_tool_underscore_bound_params_property(toolbox_tool: ToolboxTool):
    """Tests the _bound_params property returns an immutable MappingProxyType."""
    bound_params = toolbox_tool._bound_params
    assert bound_params == {"fixed_param": "fixed_value"}
    assert isinstance(bound_params, MappingProxyType)
    # Verify immutability
    with pytest.raises(TypeError):
        bound_params["new_param"] = "new_value"


def test_toolbox_tool_underscore_required_authn_params_property(
    toolbox_tool: ToolboxTool,
):
    """Tests the _required_authn_params property returns an immutable MappingProxyType."""
    required_authn_params = toolbox_tool._required_authn_params
    assert required_authn_params == {"message": ["service_a"]}
    assert isinstance(required_authn_params, MappingProxyType)
    # Verify immutability
    with pytest.raises(TypeError):
        required_authn_params["new_param"] = ["new_service"]


def test_toolbox_tool_underscore_required_authz_tokens_property(
    toolbox_tool: ToolboxTool,
):
    """Tests the _required_authz_tokens property returns an immutable MappingProxyType."""
    required_authz_tokens = toolbox_tool._required_authz_tokens
    assert required_authz_tokens == ("service_b",)
    assert isinstance(required_authz_tokens, tuple)
    # Verify immutability
    with pytest.raises(TypeError):
        required_authz_tokens[0] = "new_service"


def test_toolbox_tool_underscore_auth_service_token_getters_property(
    toolbox_tool: ToolboxTool,
):
    """Tests the _auth_service_token_getters property returns an immutable MappingProxyType."""
    auth_getters = toolbox_tool._auth_service_token_getters
    assert "service_x" in auth_getters
    assert auth_getters["service_x"]() == "token_x"
    assert isinstance(auth_getters, MappingProxyType)
    # Verify immutability
    with pytest.raises(TypeError):
        auth_getters["new_service"] = lambda: "new_token"


def test_toolbox_tool_underscore_client_headers_property(toolbox_tool: ToolboxTool):
    """Tests the _client_headers property returns an immutable MappingProxyType."""
    client_headers = toolbox_tool._client_headers
    assert client_headers == {"X-Test-Client": "client_header_value"}
    assert isinstance(client_headers, MappingProxyType)
    # Verify immutability
    with pytest.raises(TypeError):
        client_headers["new_header"] = "new_value"


# --- Test for the HTTP Warning ---
@pytest.mark.parametrize(
    "trigger_condition_params",
    [
        {"client_headers": {"X-Some-Header": "value"}},
        {"required_authn_params": {"param1": ["auth-service1"]}},
        {"required_authz_tokens": ["auth-service2"]},
        {
            "client_headers": {"X-Some-Header": "value"},
            "required_authn_params": {"param1": ["auth-service1"]},
        },
        {
            "client_headers": {"X-Some-Header": "value"},
            "required_authz_tokens": ["auth-service2"],
        },
        {
            "required_authn_params": {"param1": ["auth-service1"]},
            "required_authz_tokens": ["auth-service2"],
        },
        {
            "client_headers": {"X-Some-Header": "value"},
            "required_authn_params": {"param1": ["auth-service1"]},
            "required_authz_tokens": ["auth-service2"],
        },
    ],
    ids=[
        "client_headers_only",
        "authn_params_only",
        "authz_tokens_only",
        "headers_and_authn",
        "headers_and_authz",
        "authn_and_authz",
        "all_three_conditions",
    ],
)
def test_tool_init_http_warning_when_sensitive_info_over_http(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
    trigger_condition_params: dict,
):
    """
    Tests that a UserWarning is issued if client headers, auth params, or
    auth tokens are present and the base_url is HTTP.
    """
    expected_warning_message = (
        "Sending ID token over HTTP. User data may be exposed. "
        "Use HTTPS for secure communication."
    )

    init_kwargs = {
        "session": http_session,
        "base_url": TEST_BASE_URL,
        "name": "http_warning_tool",
        "description": sample_tool_description,
        "params": sample_tool_params,
        "required_authn_params": {},
        "required_authz_tokens": [],
        "auth_service_token_getters": {},
        "bound_params": {},
        "client_headers": {},
    }
    # Apply the specific conditions for this parametrized test
    init_kwargs.update(trigger_condition_params)

    with pytest.warns(UserWarning, match=expected_warning_message):
        ToolboxTool(**init_kwargs)


def test_tool_init_no_http_warning_if_https(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
    static_client_header: dict,
):
    """
    Tests that NO UserWarning is issued if client headers are present but
    the base_url is HTTPS.
    """
    with catch_warnings(record=True) as record:
        simplefilter("always")

        ToolboxTool(
            session=http_session,
            base_url=HTTPS_BASE_URL,
            name="https_tool",
            description=sample_tool_description,
            params=sample_tool_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters={},
            bound_params={},
            client_headers=static_client_header,
        )
    assert (
        len(record) == 0
    ), f"Expected no warnings, but got: {[f'{w.category.__name__}: {w.message}' for w in record]}"


def test_tool_init_no_http_warning_if_no_sensitive_info_on_http(
    http_session: ClientSession,
    sample_tool_params: list[ParameterSchema],
    sample_tool_description: str,
):
    """
    Tests that NO UserWarning is issued if the URL is HTTP but there are
    no client headers, auth params, or auth tokens.
    """
    with catch_warnings(record=True) as record:
        simplefilter("always")

        ToolboxTool(
            session=http_session,
            base_url=TEST_BASE_URL,
            name="http_tool_no_sensitive",
            description=sample_tool_description,
            params=sample_tool_params,
            required_authn_params={},
            required_authz_tokens=[],
            auth_service_token_getters={},
            bound_params={},
            client_headers={},
        )
    assert (
        len(record) == 0
    ), f"Expected no warnings, but got: {[f'{w.category.__name__}: {w.message}' for w in record]}"
