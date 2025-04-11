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


from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses
from pydantic import ValidationError

from toolbox_core.protocol import ParameterSchema
from toolbox_core.tool import ToolboxTool, create_docstring, resolve_value

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
def sample_tool_description() -> str:
    """Description for the sample tool."""
    return "A sample tool that processes a message and a count."


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """Provides an aiohttp ClientSession that is closed after the test."""
    async with ClientSession() as session:
        yield session


def test_create_docstring_one_param_real_schema():
    """
    Tests create_docstring with one real ParameterSchema instance.
    """
    description = "This tool does one thing."
    params = [
        ParameterSchema(
            name="input_file", type="string", description="Path to the input file."
        )
    ]

    result_docstring = create_docstring(description, params)

    expected_docstring = (
        "This tool does one thing.\n\n"
        "Args:\n"
        "    input_file (str): Path to the input file."
    )

    assert result_docstring == expected_docstring


def test_create_docstring_multiple_params_real_schema():
    """
    Tests create_docstring with multiple real ParameterSchema instances.
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

    result_docstring = create_docstring(description, params)

    expected_docstring = (
        "This tool does multiple things.\n\n"
        "Args:\n"
        "    query (str): The search query.\n"
        "    max_results (int): Maximum results to return.\n"
        "    verbose (bool): Enable verbose output."
    )

    assert result_docstring == expected_docstring


def test_create_docstring_no_description_real_schema():
    """
    Tests create_docstring with empty description and one real ParameterSchema.
    """
    description = ""
    params = [
        ParameterSchema(
            name="config_id", type="string", description="The ID of the configuration."
        )
    ]

    result_docstring = create_docstring(description, params)

    expected_docstring = (
        "\n\nArgs:\n" "    config_id (str): The ID of the configuration."
    )

    assert result_docstring == expected_docstring
    assert result_docstring.startswith("\n\nArgs:")
    assert "config_id (str): The ID of the configuration." in result_docstring


def test_create_docstring_no_params():
    """
    Tests create_docstring when the params list is empty.
    """
    description = "This is a tool description."
    params = []

    result_docstring = create_docstring(description, params)

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
            auth_service_token_getters={},
            bound_params={},
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
            auth_service_token_getters={},
            bound_params={},
        )

        assert callable(tool_instance)

        with pytest.raises(ValidationError) as exc_info:
            await tool_instance(message="hello", count="not-a-number")

        assert (
            "1 validation error for sample_tool\ncount\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='not-a-number', input_type=str]\n    For further information visit https://errors.pydantic.dev/2.11/v/int_parsing"
            in str(exc_info.value)
        )
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
