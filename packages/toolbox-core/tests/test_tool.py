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

import pytest
from unittest.mock import AsyncMock, MagicMock
from inspect import Parameter, Signature
from typing import Any, Optional, Callable

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
            Parameter("arg1", Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
            Parameter("opt_arg", Parameter.POSITIONAL_OR_KEYWORD, default=123, annotation=Optional[int]),
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
    async def test_initialization_and_introspection(self, tool: ToolboxTool, tool_details: dict):
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
        configure_mock_response: Callable
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
        configure_mock_response: Callable
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
        configure_mock_response: Callable
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
        configure_mock_response: Callable
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
        self,
        tool: ToolboxTool,
        mock_session: MagicMock
    ):
        with pytest.raises(TypeError):
            await tool("val1", 2, 3)

        with pytest.raises(TypeError):
            await tool("val1", non_existent_arg="bad")

        with pytest.raises(TypeError):
            await tool(opt_arg=500)

        mock_session.post.assert_not_called()