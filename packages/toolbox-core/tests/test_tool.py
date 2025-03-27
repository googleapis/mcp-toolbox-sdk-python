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

from inspect import Parameter, Signature
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from toolbox_core.tool import ToolboxTool


class TestToolboxTool:
    @pytest.fixture
    def mock_session(self) -> MagicMock:  # Added self
        session = MagicMock()
        session.post = MagicMock()
        return session

    @pytest.fixture
    def tool_params(self) -> list[Parameter]:
        return [
            Parameter("arg1", Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
            Parameter(
                "opt_arg",
                Parameter.POSITIONAL_OR_KEYWORD,
                default=123,
                annotation=Optional[int],
            ),
            Parameter("req_kwarg", Parameter.KEYWORD_ONLY, annotation=bool),  # Added back
        ]

    @pytest.fixture
    def tool_details(self, tool_params: list[Parameter]) -> dict[str, Any]:
        """Provides common details for constructing the test tool."""
        base_url = "http://fake-toolbox.com"
        tool_name = "test_tool"
        params = tool_params
        full_signature = Signature(parameters=params, return_annotation=str)
        public_signature = Signature(parameters=params, return_annotation=str)
        full_annotations = {"arg1": str, "opt_arg": Optional[int], "req_kwarg": bool}
        public_annotations = full_annotations.copy()

        return {
            "base_url": base_url,
            "name": tool_name,
            "desc": "A tool for testing.",
            "params": params,
            "full_signature": full_signature,
            "expected_url": f"{base_url}/api/tool/{tool_name}/invoke",
            "public_signature": public_signature,
            "public_annotations": public_annotations,
        }

    @pytest.fixture
    def tool(self, mock_session: MagicMock, tool_details: dict) -> ToolboxTool:
        return ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],
            bound_params=None,
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
        assert tool.__signature__ == tool_details["public_signature"]
        assert tool.__annotations__ == tool_details["public_annotations"]
        assert tool._ToolboxTool__bound_params == {}
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
        req_kwarg_val = True
        result = await tool(arg1_val, opt_arg=opt_arg_val, req_kwarg=req_kwarg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            payload={"arg1": arg1_val, "opt_arg": opt_arg_val, "req_kwarg": req_kwarg_val},
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

    # Bound Params tests
    @pytest.fixture
    def bound_arg1_value(self) -> str:
        return "statically_bound_arg1"

    @pytest.fixture
    def tool_with_bound_arg1(
            self, mock_session: MagicMock, tool_details: dict[str, Any], bound_arg1_value: str
    ) -> ToolboxTool:
        bound_params = {"arg1": bound_arg1_value}
        return ToolboxTool(
            session=mock_session,
            base_url=tool_details["base_url"],
            name=tool_details["name"],
            desc=tool_details["desc"],
            params=tool_details["params"],  # Use corrected params
            bound_params=bound_params,
        )
    @pytest.mark.asyncio
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
        req_kwarg_val = True  # The only remaining required arg

        # Call *without* providing arg1, but provide the others
        result = await tool_with_bound_arg1(opt_arg=opt_arg_val, req_kwarg=req_kwarg_val)

        assert result == expected_result
        mock_session.post.assert_called_once_with(
            tool_details["expected_url"],
            # Payload should include the bound value for arg1
            payload={"arg1": bound_arg1_value, "opt_arg": opt_arg_val, "req_kwarg": req_kwarg_val},
        )
        mock_session.post.return_value.__aenter__.return_value.json.assert_awaited_once()
