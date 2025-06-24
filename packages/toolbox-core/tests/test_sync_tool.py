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
from inspect import Parameter, Signature
from threading import Thread
from typing import Any, Callable, Mapping, Union
from unittest.mock import MagicMock, Mock, create_autospec, patch

import pytest

from toolbox_core.sync_tool import ToolboxSyncTool
from toolbox_core.tool import ToolboxTool


@pytest.fixture
def mock_async_tool() -> MagicMock:
    """Fixture for an auto-specced MagicMock simulating a ToolboxTool instance."""
    tool = create_autospec(ToolboxTool, instance=True)
    tool.__name__ = "mock_async_tool_name"
    tool.__doc__ = "Mock async tool documentation."

    # Create a simple signature for the mock tool
    param_a = Parameter("a", Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
    param_b = Parameter(
        "b", Parameter.POSITIONAL_OR_KEYWORD, annotation=int, default=10
    )
    tool.__signature__ = Signature(parameters=[param_a, param_b])

    tool.__annotations__ = {"a": str, "b": int, "return": str}

    tool.add_auth_token_getters.return_value = create_autospec(
        ToolboxTool, instance=True
    )
    tool.bind_params.return_value = create_autospec(ToolboxTool, instance=True)

    return tool


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Fixture for an event loop."""
    # Using asyncio.get_event_loop() might be problematic if no loop is set.
    # For this test setup, we'll mock `run_coroutine_threadsafe` directly.
    return Mock(spec=asyncio.AbstractEventLoop)


@pytest.fixture
def mock_thread() -> MagicMock:
    """Fixture for a mock Thread."""
    return MagicMock(spec=Thread)


@pytest.fixture
def toolbox_sync_tool(
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
) -> ToolboxSyncTool:
    """Fixture for a ToolboxSyncTool instance."""
    return ToolboxSyncTool(mock_async_tool, event_loop, mock_thread)


def test_toolbox_sync_tool_init_success(
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
):
    """Tests successful initialization of ToolboxSyncTool."""
    tool = ToolboxSyncTool(mock_async_tool, event_loop, mock_thread)
    assert tool._ToolboxSyncTool__async_tool is mock_async_tool
    assert tool._ToolboxSyncTool__loop is event_loop
    assert tool._ToolboxSyncTool__thread is mock_thread
    assert tool.__qualname__ == f"ToolboxSyncTool.{mock_async_tool.__name__}"


def test_toolbox_sync_tool_init_type_error():
    """Tests TypeError if async_tool is not a ToolboxTool instance."""
    with pytest.raises(
        TypeError, match="async_tool must be an instance of ToolboxTool"
    ):
        ToolboxSyncTool("not_a_toolbox_tool", Mock(), Mock())


def test_toolbox_sync_tool_name_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the __name__ property."""
    assert toolbox_sync_tool.__name__ == mock_async_tool.__name__


def test_toolbox_sync_tool_doc_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the __doc__ property."""
    assert toolbox_sync_tool.__doc__ == mock_async_tool.__doc__

    # Test with __doc__ = None
    mock_async_tool.__doc__ = None
    sync_tool_no_doc = ToolboxSyncTool(mock_async_tool, Mock(), Mock())
    assert sync_tool_no_doc.__doc__ is None


def test_toolbox_sync_tool_signature_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the __signature__ property."""
    assert toolbox_sync_tool.__signature__ is mock_async_tool.__signature__


def test_toolbox_sync_tool_annotations_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the __annotations__ property."""
    assert toolbox_sync_tool.__annotations__ is mock_async_tool.__annotations__


def test_toolbox_sync_tool_underscore_name_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _name property."""
    assert toolbox_sync_tool._name == mock_async_tool._name


def test_toolbox_sync_tool_underscore_description_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _description property."""
    assert toolbox_sync_tool._description == mock_async_tool._description


def test_toolbox_sync_tool_underscore_params_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _params property."""
    assert toolbox_sync_tool._params == mock_async_tool._params


def test_toolbox_sync_tool_underscore_bound_params_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _bound_params property."""
    assert toolbox_sync_tool._bound_params == mock_async_tool._bound_params


def test_toolbox_sync_tool_underscore_required_authn_params_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _required_authn_params property."""
    assert (
        toolbox_sync_tool._required_authn_params
        == mock_async_tool._required_authn_params
    )


def test_toolbox_sync_tool_underscore_required_authz_tokens_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _required_authz_tokens property."""
    assert (
        toolbox_sync_tool._required_authz_tokens
        == mock_async_tool._required_authz_tokens
    )


def test_toolbox_sync_tool_underscore_auth_service_token_getters_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _auth_service_token_getters property."""
    assert (
        toolbox_sync_tool._auth_service_token_getters
        is mock_async_tool._auth_service_token_getters
    )


def test_toolbox_sync_tool_underscore_client_headers_property(
    toolbox_sync_tool: ToolboxSyncTool, mock_async_tool: MagicMock
):
    """Tests the _client_headers property."""
    assert toolbox_sync_tool._client_headers is mock_async_tool._client_headers


@patch("asyncio.run_coroutine_threadsafe")
def test_toolbox_sync_tool_call(
    mock_run_coroutine_threadsafe: MagicMock,
    toolbox_sync_tool: ToolboxSyncTool,
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
):
    """Tests the __call__ method."""
    mock_future = MagicMock()
    expected_result = "call_result"
    mock_future.result.return_value = expected_result
    mock_run_coroutine_threadsafe.return_value = mock_future

    args_tuple = ("test_arg",)
    kwargs_dict = {"kwarg1": "value1"}

    # Create a mock coroutine to be returned by async_tool.__call__
    mock_coro = MagicMock(name="mock_coro_returned_by_async_tool")
    mock_async_tool.return_value = mock_coro

    result = toolbox_sync_tool(*args_tuple, **kwargs_dict)

    mock_async_tool.assert_called_once_with(*args_tuple, **kwargs_dict)
    mock_run_coroutine_threadsafe.assert_called_once_with(mock_coro, event_loop)
    mock_future.result.assert_called_once_with()
    assert result == expected_result


def test_toolbox_sync_tool_add_auth_token_getters(
    toolbox_sync_tool: ToolboxSyncTool,
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
):
    """Tests the add_auth_token_getters method."""
    auth_getters: Mapping[str, Callable[[], str]] = {"service1": lambda: "token1"}

    new_mock_async_tool = mock_async_tool.add_auth_token_getters.return_value
    new_mock_async_tool.__name__ = "new_async_tool_with_auth"

    new_sync_tool = toolbox_sync_tool.add_auth_token_getters(auth_getters)

    mock_async_tool.add_auth_token_getters.assert_called_once_with(auth_getters)

    assert isinstance(new_sync_tool, ToolboxSyncTool)
    assert new_sync_tool is not toolbox_sync_tool
    assert new_sync_tool._ToolboxSyncTool__async_tool is new_mock_async_tool
    assert new_sync_tool._ToolboxSyncTool__loop is event_loop  # Should be the same loop
    assert (
        new_sync_tool._ToolboxSyncTool__thread is mock_thread
    )  # Should be the same thread
    assert (
        new_sync_tool.__qualname__ == f"ToolboxSyncTool.{new_mock_async_tool.__name__}"
    )


def test_toolbox_sync_tool_add_auth_token_getter(
    toolbox_sync_tool: ToolboxSyncTool,
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
):
    """Tests the add_auth_token_getter method."""
    auth_service = "service1"
    auth_token_getter = lambda: "token1"

    new_mock_async_tool = mock_async_tool.add_auth_token_getters.return_value
    new_mock_async_tool.__name__ = "new_async_tool_with_auth"

    new_sync_tool = toolbox_sync_tool.add_auth_token_getter(
        auth_service, auth_token_getter
    )

    mock_async_tool.add_auth_token_getters.assert_called_once_with(
        {auth_service: auth_token_getter}
    )

    assert isinstance(new_sync_tool, ToolboxSyncTool)
    assert new_sync_tool is not toolbox_sync_tool
    assert new_sync_tool._ToolboxSyncTool__async_tool is new_mock_async_tool
    assert new_sync_tool._ToolboxSyncTool__loop is event_loop  # Should be the same loop
    assert (
        new_sync_tool._ToolboxSyncTool__thread is mock_thread
    )  # Should be the same thread
    assert (
        new_sync_tool.__qualname__ == f"ToolboxSyncTool.{new_mock_async_tool.__name__}"
    )


def test_toolbox_sync_tool_bind_params(
    toolbox_sync_tool: ToolboxSyncTool,
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
):
    """Tests the bind_params method."""
    bound_params: Mapping[str, Union[Callable[[], Any], Any]] = {
        "param1": "value1",
        "param2": lambda: "value2",
    }

    new_mock_async_tool = mock_async_tool.bind_params.return_value
    new_mock_async_tool.__name__ = "new_async_tool_with_bound_params"

    new_sync_tool = toolbox_sync_tool.bind_params(bound_params)

    mock_async_tool.bind_params.assert_called_once_with(bound_params)

    assert isinstance(new_sync_tool, ToolboxSyncTool)
    assert new_sync_tool is not toolbox_sync_tool
    assert new_sync_tool._ToolboxSyncTool__async_tool is new_mock_async_tool
    assert new_sync_tool._ToolboxSyncTool__loop is event_loop
    assert new_sync_tool._ToolboxSyncTool__thread is mock_thread
    assert (
        new_sync_tool.__qualname__ == f"ToolboxSyncTool.{new_mock_async_tool.__name__}"
    )


def test_toolbox_sync_tool_bind_param(
    toolbox_sync_tool: ToolboxSyncTool,
    mock_async_tool: MagicMock,
    event_loop: asyncio.AbstractEventLoop,
    mock_thread: MagicMock,
):
    """Tests the bind_param method."""
    param_name = "my_param"
    param_value = "my_value"

    new_mock_async_tool = mock_async_tool.bind_params.return_value
    new_mock_async_tool.__name__ = "new_async_tool_with_single_bound_param"

    new_sync_tool = toolbox_sync_tool.bind_param(param_name, param_value)

    mock_async_tool.bind_params.assert_called_once_with({param_name: param_value})

    assert isinstance(new_sync_tool, ToolboxSyncTool)
    assert new_sync_tool is not toolbox_sync_tool
    assert new_sync_tool._ToolboxSyncTool__async_tool is new_mock_async_tool
    assert new_sync_tool._ToolboxSyncTool__loop is event_loop
    assert new_sync_tool._ToolboxSyncTool__thread is mock_thread
    assert (
        new_sync_tool.__qualname__ == f"ToolboxSyncTool.{new_mock_async_tool.__name__}"
    )
