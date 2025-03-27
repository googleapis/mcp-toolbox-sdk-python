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

from inspect import Signature
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from toolbox_core.protocol import ParameterSchema
from toolbox_core.tool import ToolboxTool


class TestToolboxTool:
    @pytest.fixture
    def mock_session(self) -> MagicMock:  # Added self
        session = MagicMock()
        session.post = MagicMock()
        return session

    @pytest.fixture
    def tool_details(self) -> dict:
        base_url = "http://fake-toolbox.com"
        tool_name = "test_tool"
        params = [
            ParameterSchema("arg1", Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
            ParameterSchema(
                "opt_arg",
                Parameter.POSITIONAL_OR_KEYWORD,
                default=123,
                annotation=Optional[int],
            ),
        ]
        return {
            "base_url": base_url,
            "name": tool_name,
            "desc": "A tool for testing.",
            "params": params,
            "signature": Signature(parameters=params, return_annotation=str),
            "expected_url": f"{base_url}/api/tool/{tool_name}/invoke",
            "annotations": {"arg1": str, "opt_arg": Optional[int]},
        }

    @pytest.fixture
    def tool(self, mock_session: MagicMock, tool_details: dict) -> ToolboxTool:
        return ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
        )

    @pytest.fixture
    def configure_mock_response(self, mock_session: MagicMock) -> Callable:
        def _configure(json_data: Any, status: int = 200):
            mock_resp = MagicMock()
            mock_resp.status = status
            mock_resp.json = AsyncMock(return_value=json_data)
            mock_resp.__aenter__.return_value = mock_resp
            mock_resp.__aexit__.return_value = None
            mock_session.post.return_value = mock_resp

        return _configure

    @pytest.mark.asyncio
    async def test_initialization_and_introspection(
        self, tool: ToolboxTool, tool_details: dict
    ):
        """Verify attributes are set correctly during initialization."""
        assert tool.__name__ == tool_details["name"]
        assert tool.__doc__ == tool_details["desc"]
        assert tool._ToolboxTool__url == tool_details["expected_url"]
        assert tool._ToolboxTool__session is tool._ToolboxTool__session
        assert tool.__signature__ == tool_details["signature"]
        assert tool.__annotations__ == tool_details["annotations"]
        # assert hasattr(tool, "__qualname__")

    @pytest.mark.asyncio
    async def test_call_success(
        self,
        tool: ToolboxTool,
        mock_session: MagicMock,
        tool_details: dict,
        configure_mock_response: Callable,
    ):
        expected_result = "Operation successful!"
        configure_mock_response({"result": expected_result})

        arg1_val = "test_value"
        opt_arg_val = 456
        result = await tool(arg1_val, opt_arg=opt_arg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            json={"arg1": arg1_val, "opt_arg": opt_arg_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_success_with_defaults(
        self,
        tool: ToolboxTool,
        mock_session: MagicMock,
        tool_details: dict,
        configure_mock_response: Callable,
    ):
        expected_result = "Default success!"
        configure_mock_response({"result": expected_result})

        arg1_val = "another_test"
        default_opt_val = tool_details["params"][1].default
        result = await tool(arg1_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            json={"arg1": arg1_val, "opt_arg": default_opt_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_api_error(
        self,
        tool: ToolboxTool,
        mock_session: MagicMock,
        tool_details: dict,
        configure_mock_response: Callable,
    ):
        error_message = "Tool execution failed on server"
        configure_mock_response({"error": error_message})
        default_opt_val = tool_details["params"][1].default

        with pytest.raises(Exception) as exc_info:
            await tool("some_arg")

        assert str(exc_info.value) == error_message
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            json={"arg1": "some_arg", "opt_arg": default_opt_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_missing_result_key(
        self,
        tool: ToolboxTool,
        mock_session: MagicMock,
        tool_details: dict,
        configure_mock_response: Callable,
    ):
        fallback_response = {"status": "completed", "details": "some info"}
        configure_mock_response(fallback_response)
        default_opt_val = tool_details["params"][1].default

        result = await tool("value_for_arg1")

        assert result == fallback_response
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            json={"arg1": "value_for_arg1", "opt_arg": default_opt_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_call_invalid_arguments_type_error(
        self, tool: ToolboxTool, mock_session: MagicMock
    ):
        with pytest.raises(TypeError):
            await tool("val1", 2, 3)

        with pytest.raises(TypeError):
            await tool("val1", non_existent_arg="bad")

        with pytest.raises(TypeError):
            await tool(opt_arg=500)

        mock_session.post.assert_not_called()

    @pytest.fixture
    def bound_arg1_value(self) -> str:
        return "statically_bound_arg1"

    @pytest.fixture
    def tool_with_bound_arg1(
            self, mock_session: MagicMock, tool_details: dict[str, Any], bound_arg1_value: str
    ) -> ToolboxTool:
        """Provides a tool with 'arg1' statically bound."""
        bound_params = {"arg1": bound_arg1_value}
        return ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=bound_params,
        )

    async def test_bound_parameter_static_value_call(
            self,
            tool_with_bound_arg1: ToolboxTool,
            mock_session: MagicMock,
            tool_details: dict[str, Any],
            configure_mock_response: Callable,
            bound_arg1_value: str,
    ):
        """Test calling a tool with a statically bound parameter."""
        expected_result = "Bound call success!"
        configure_mock_response(json_data={"result": expected_result})

        opt_arg_val = 789
        req_kwarg_val = True
        default_opt_val = tool_details["params"][1].default  # Not used here, but for clarity

        # Call *without* providing arg1
        result = await tool_with_bound_arg1(opt_arg=opt_arg_val, req_kwarg=req_kwarg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            # Payload should include the bound value for arg1
            json={"arg1": bound_arg1_value, "opt_arg": opt_arg_val, "req_kwarg": req_kwarg_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    async def test_bound_parameter_static_value_introspection(
            self, tool_with_bound_arg1: ToolboxTool, tool_details: dict[str, Any]
    ):
        """Verify the public signature excludes the bound parameter 'arg1'."""
        assert "arg1" not in tool_with_bound_arg1.__signature__.parameters
        assert "arg1" not in tool_with_bound_arg1.__annotations__

        # Check remaining parameters are present
        assert "opt_arg" in tool_with_bound_arg1.__signature__.parameters
        assert "req_kwarg" in tool_with_bound_arg1.__signature__.parameters
        assert tool_with_bound_arg1.__signature__.parameters["opt_arg"].annotation == Optional[int]
        assert tool_with_bound_arg1.__signature__.parameters["req_kwarg"].annotation == bool

    async def test_bound_parameter_callable_value_call(
            self,
            mock_session: MagicMock,
            tool_details: dict[str, Any],
            configure_mock_response: Callable,
    ):
        """Test calling a tool with a parameter bound to a callable."""
        callable_value = "dynamic_value"
        callable_mock = MagicMock(return_value=callable_value)
        bound_params = {"arg1": callable_mock}

        tool_bound_callable = ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=bound_params,
        )

        expected_result = "Callable bound success!"
        configure_mock_response(json_data={"result": expected_result})

        opt_arg_val = 999
        req_kwarg_val = False

        # Call *without* providing arg1
        result = await tool_bound_callable(opt_arg=opt_arg_val, req_kwarg=req_kwarg_val)

        assert result == expected_result
        # Verify the callable was executed exactly once
        callable_mock.assert_called_once()

        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            # Payload should include the *result* of the callable
            json={"arg1": callable_value, "opt_arg": opt_arg_val, "req_kwarg": req_kwarg_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()

    async def test_bound_parameter_callable_evaluation_error(
            self,
            mock_session: MagicMock,
            tool_details: dict[str, Any],
    ):
        """Test that RuntimeError is raised if bound callable evaluation fails."""
        error_message = "Callable evaluation failed!"

        def failing_callable():
            raise ValueError(error_message)

        bound_params = {"arg1": failing_callable}
        tool_bound_failing = ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=bound_params,
        )

        with pytest.raises(RuntimeError) as exc_info:
            await tool_bound_failing(opt_arg=1, req_kwarg=True)  # Provide other args

        # Check that the original exception message is part of the RuntimeError
        assert error_message in str(exc_info.value)
        assert "Error evaluating argument 'arg1'" in str(exc_info.value)

        # Ensure the API call was *not* made
        mock_session.post.assert_not_called()

    async def test_bound_parameter_conflict_error(
            self, tool_with_bound_arg1: ToolboxTool, mock_session: MagicMock, bound_arg1_value: str
    ):
        """Test TypeError when providing an argument that is already bound."""
        conflicting_arg1_val = "call_time_value"

        with pytest.raises(TypeError) as exc_info:
            # Attempt to provide 'arg1' again during the call
            await tool_with_bound_arg1(arg1=conflicting_arg1_val, req_kwarg=True)

        assert "Cannot provide value during call for already bound argument(s): arg1" in str(exc_info.value)

        # Ensure the API call was *not* made
        mock_session.post.assert_not_called()

    async def test_bound_parameter_overrides_default(
            self,
            mock_session: MagicMock,
            tool_details: dict[str, Any],
            configure_mock_response: Callable,
    ):
        """Test that a bound value for a parameter with a default overrides the default."""
        bound_opt_arg_value = 999  # Different from the default of 123
        bound_params = {"opt_arg": bound_opt_arg_value}

        tool_bound_default = ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=bound_params,
        )

        expected_result = "Default override success!"
        configure_mock_response(json_data={"result": expected_result})

        arg1_val = "required_arg_val"
        req_kwarg_val = True

        # Call *without* providing opt_arg
        result = await tool_bound_default(arg1_val, req_kwarg=req_kwarg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            # Payload should include the bound value for opt_arg, not the default
            json={"arg1": arg1_val, "opt_arg": bound_opt_arg_value, "req_kwarg": req_kwarg_val},
        )

    async def test_multiple_bound_parameters(
            self,
            mock_session: MagicMock,
            tool_details: dict[str, Any],
            configure_mock_response: Callable,
    ):
        """Test binding multiple parameters."""
        bound_arg1 = "multi_bound_1"
        bound_opt_arg = 555
        bound_params = {
            "arg1": bound_arg1,
            "opt_arg": bound_opt_arg,
        }

        tool_multi_bound = ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=bound_params,
        )

        # Check introspection - only req_kwarg should remain
        assert list(tool_multi_bound.__signature__.parameters.keys()) == ["req_kwarg"]

        expected_result = "Multi-bound success!"
        configure_mock_response(json_data={"result": expected_result})

        req_kwarg_val = False
        # Call providing only the remaining unbound argument
        result = await tool_multi_bound(req_kwarg=req_kwarg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            # Payload should include both bound values and the called value
            json={"arg1": bound_arg1, "opt_arg": bound_opt_arg, "req_kwarg": req_kwarg_val},
        )