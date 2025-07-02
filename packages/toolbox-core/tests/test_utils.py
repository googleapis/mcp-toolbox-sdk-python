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


import asyncio
from typing import Type
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ValidationError

from toolbox_core.protocol import ParameterSchema
from toolbox_core.utils import (
    create_func_docstring,
    identify_auth_requirements,
    params_to_pydantic_model,
    resolve_value,
)


def create_param_mock(name: str, description: str, annotation: Type) -> Mock:
    """Creates a mock for ParameterSchema."""
    param_mock = Mock(spec=ParameterSchema)
    param_mock.name = name
    param_mock.description = description
    param_mock.required = True

    mock_param_info = Mock()
    mock_param_info.annotation = annotation

    param_mock.to_param.return_value = mock_param_info
    return param_mock


def test_create_func_docstring_no_params():
    """Test create_func_docstring with no parameters."""
    description = "This is a tool description."
    params = []
    expected_docstring = "This is a tool description."
    assert create_func_docstring(description, params) == expected_docstring


def test_create_func_docstring_with_params():
    """Test create_func_docstring with multiple parameters using mocks."""
    description = "Tool description."
    params = [
        create_param_mock(
            name="param1", description="First parameter.", annotation=str
        ),
        create_param_mock(name="count", description="A number.", annotation=int),
    ]
    expected_docstring = """Tool description.

Args:
    param1 (str): First parameter.
    count (int): A number."""
    assert create_func_docstring(description, params) == expected_docstring


def test_create_func_docstring_empty_description():
    """Test create_func_docstring with an empty description using mocks."""
    description = ""
    params = [
        create_param_mock(
            name="param1", description="First parameter.", annotation=str
        ),
    ]
    expected_docstring = """

Args:
    param1 (str): First parameter."""
    assert create_func_docstring(description, params) == expected_docstring


def test_identify_auth_requirements_none_required():
    """Test when no authentication parameters or authorization tokens are required initially."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens: list[str] = []
    auth_service_names = ["service_a", "service_b"]
    expected_params = {}
    expected_authz: list[str] = []
    expected_used = set()
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_requirements_all_covered():
    """Test when all required authn parameters are covered, no authz tokens."""
    req_authn_params = {
        "token_a": ["service_a"],
        "token_b": ["service_b", "service_c"],
    }
    req_authz_tokens: list[str] = []
    auth_service_names = ["service_a", "service_b"]
    expected_params = {}
    expected_authz: list[str] = []
    expected_used = {"service_a", "service_b"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_requirements_some_covered():
    """Test when some authn parameters are covered, and some are not, no authz tokens."""
    req_authn_params = {
        "token_a": ["service_a"],
        "token_b": ["service_b", "service_c"],
        "token_d": ["service_d"],
        "token_e": ["service_e", "service_f"],
    }
    req_authz_tokens: list[str] = []
    auth_service_names = ["service_a", "service_b"]
    expected_params = {
        "token_d": ["service_d"],
        "token_e": ["service_e", "service_f"],
    }
    expected_authz: list[str] = []
    expected_used = {"service_a", "service_b"}

    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_requirements_none_covered():
    """Test when none of the required authn parameters are covered, no authz tokens."""
    req_authn_params = {
        "token_d": ["service_d"],
        "token_e": ["service_e", "service_f"],
    }
    req_authz_tokens: list[str] = []
    auth_service_names = ["service_a", "service_b"]
    expected_params = {
        "token_d": ["service_d"],
        "token_e": ["service_e", "service_f"],
    }
    expected_authz: list[str] = []
    expected_used = set()
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_requirements_no_available_services():
    """Test when no authn services are available, no authz tokens."""
    req_authn_params = {
        "token_a": ["service_a"],
        "token_b": ["service_b", "service_c"],
    }
    req_authz_tokens: list[str] = []
    auth_service_names: list[str] = []
    expected_params = {
        "token_a": ["service_a"],
        "token_b": ["service_b", "service_c"],
    }
    expected_authz: list[str] = []
    expected_used = set()
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_requirements_empty_services_for_param():
    """Test edge case: authn param requires an empty list of services, no authz tokens."""
    req_authn_params = {
        "token_x": [],
    }
    req_authz_tokens: list[str] = []
    auth_service_names = ["service_a"]
    expected_params = {
        "token_x": [],
    }
    expected_authz: list[str] = []
    expected_used = set()
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_identify_auth_params_only_authz_empty():
    """Test with empty req_authz_tokens and no authn params."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens: list[str] = []
    auth_service_names = ["s1"]
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == ({}, [], set())


def test_identify_auth_params_authz_all_covered():
    """Test when all req_authz_tokens are covered by auth_service_names."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens = ["s1", "s2"]
    auth_service_names = ["s1", "s2", "s3"]
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == ({}, [], {"s1", "s2"})


def test_identify_auth_params_authz_partially_covered_by_available():
    """Test when some req_authz_tokens are covered."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens = ["s1", "s2"]
    auth_service_names = ["s1", "s3"]
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == ({}, [], {"s1"})


def test_identify_auth_params_authz_none_covered():
    """Test when none of req_authz_tokens are covered by auth_service_names."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens = ["s1", "s2"]
    auth_service_names = ["s3", "s4"]
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == ({}, ["s1", "s2"], set())


def test_identify_auth_params_authz_none_covered_empty_available():
    """Test with req_authz_tokens but no available services."""
    req_authn_params: dict[str, list[str]] = {}
    req_authz_tokens = ["s1", "s2"]
    auth_service_names: list[str] = []
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == ({}, ["s1", "s2"], set())


def test_identify_auth_params_authn_covered_authz_uncovered():
    """Test authn params covered, but authz tokens are not."""
    req_authn_params = {"param1": ["s_authn1"]}
    req_authz_tokens = ["s_authz_needed1", "s_authz_needed2"]
    auth_service_names = ["s_authn1", "s_other"]
    expected_params = {}
    expected_authz: list[str] = ["s_authz_needed1", "s_authz_needed2"]
    expected_used = {"s_authn1"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (expected_params, expected_authz, expected_used)


def test_identify_auth_params_authn_uncovered_authz_covered():
    """Test authn params not covered, but authz tokens are covered."""
    req_authn_params = {"param1": ["s_authn_needed"]}
    req_authz_tokens = ["s_authz1"]
    auth_service_names = ["s_authz1", "s_other"]
    expected_params = {"param1": ["s_authn_needed"]}
    expected_authz: list[str] = []
    expected_used = {"s_authz1"}

    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (expected_params, expected_authz, expected_used)


def test_identify_auth_params_authn_and_authz_covered_no_overlap():
    """Test both authn and authz are covered by different services."""
    req_authn_params = {"param1": ["s_authn1"]}
    req_authz_tokens = ["s_authz1"]
    auth_service_names = ["s_authn1", "s_authz1"]
    expected_params = {}
    expected_authz: list[str] = []
    expected_used = {"s_authn1", "s_authz1"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (expected_params, expected_authz, expected_used)


def test_identify_auth_params_authn_and_authz_covered_with_overlap():
    """Test both authn and authz are covered, with some services overlapping."""
    req_authn_params = {"param1": ["s_common"], "param2": ["s_authn_specific_avail"]}
    req_authz_tokens = ["s_common", "s_authz_specific_avail"]
    auth_service_names = [
        "s_common",
        "s_authz_specific_avail",
        "s_authn_specific_avail",
    ]
    expected_params = {}
    expected_authz: list[str] = []
    expected_used = {"s_common", "s_authz_specific_avail", "s_authn_specific_avail"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (expected_params, expected_authz, expected_used)


def test_identify_auth_params_authn_and_authz_covered_with_overlap_same_param():
    """Test both authn and authz are covered, with some services overlapping within same param."""
    req_authn_params = {"param1": ["s_common", "s_authn_specific_avail"]}
    req_authz_tokens = ["s_common", "s_authz_specific_avail"]
    auth_service_names = [
        "s_common",
        "s_authz_specific_avail",
        "s_authn_specific_avail",
    ]
    expected_params = {}
    expected_authz: list[str] = []
    expected_used = {"s_common", "s_authz_specific_avail", "s_authn_specific_avail"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (expected_params, expected_authz, expected_used)


def test_identify_auth_params_complex_scenario():
    """Test a more complex scenario with partial coverage for both authn and authz."""
    req_authn_params = {"p1": ["s1", "s2"], "p2": ["s3"]}
    req_authz_tokens = ["s4", "s6"]
    auth_service_names = ["s1", "s4", "s5"]
    expected_params = {"p2": ["s3"]}
    expected_authz: list[str] = []
    expected_used = {"s1", "s4"}
    result = identify_auth_requirements(
        req_authn_params, req_authz_tokens, auth_service_names
    )
    assert result == (
        expected_params,
        expected_authz,
        expected_used,
    )


def test_params_to_pydantic_model_no_params():
    """Test creating a Pydantic model with no parameters."""
    tool_name = "NoParamTool"
    params = []
    Model = params_to_pydantic_model(tool_name, params)

    assert issubclass(Model, BaseModel)
    assert Model.__name__ == tool_name
    assert not Model.model_fields

    instance = Model()
    assert isinstance(instance, BaseModel)


def test_params_to_pydantic_model_with_params():
    """Test creating a Pydantic model with various parameter types using mocks."""
    tool_name = "MyTool"
    params = [
        create_param_mock(name="name", description="User name", annotation=str),
        create_param_mock(name="age", description="User age", annotation=int),
        create_param_mock(
            name="is_active", description="Activity status", annotation=bool
        ),
    ]
    Model = params_to_pydantic_model(tool_name, params)

    assert issubclass(Model, BaseModel)
    assert Model.__name__ == tool_name
    assert len(Model.model_fields) == 3

    assert "name" in Model.model_fields
    assert Model.model_fields["name"].annotation == str
    assert Model.model_fields["name"].description == "User name"

    assert "age" in Model.model_fields
    assert Model.model_fields["age"].annotation == int
    assert Model.model_fields["age"].description == "User age"

    assert "is_active" in Model.model_fields
    assert Model.model_fields["is_active"].annotation == bool
    assert Model.model_fields["is_active"].description == "Activity status"

    instance = Model(name="Alice", age=30, is_active=True)
    assert instance.name == "Alice"
    assert instance.age == 30
    assert instance.is_active is True

    with pytest.raises(ValidationError):
        Model(name="Bob", age="thirty", is_active=True)


@pytest.mark.asyncio
async def test_resolve_value_plain_value():
    """Test resolving a plain, non-callable value."""
    value = 123
    assert await resolve_value(value) == 123

    value = "hello"
    assert await resolve_value(value) == "hello"

    value = None
    assert await resolve_value(value) is None


@pytest.mark.asyncio
async def test_resolve_value_sync_callable():
    """Test resolving a synchronous callable using Mock."""
    mock_sync_func = Mock(return_value="sync result")
    assert await resolve_value(mock_sync_func) == "sync result"
    mock_sync_func.assert_called_once()
    assert await resolve_value(lambda: [1, 2, 3]) == [1, 2, 3]


@pytest.mark.asyncio
async def test_resolve_value_async_callable():
    """Test resolving an asynchronous callable (coroutine function)."""

    async def async_func():
        await asyncio.sleep(0.01)
        return "async result"

    assert await resolve_value(async_func) == "async result"

    async def another_async_func():
        return {"key": "value"}

    assert await resolve_value(another_async_func) == {"key": "value"}
