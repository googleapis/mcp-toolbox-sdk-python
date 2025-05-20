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

import types  # For MappingProxyType
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from llama_index.core.tools.types import ToolOutput
from pydantic import ValidationError
from toolbox_core.protocol import ParameterSchema as CoreParameterSchema
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool

from toolbox_llamaindex.async_tools import AsyncToolboxTool


@pytest.mark.asyncio
class TestAsyncToolboxTool:
    @pytest.fixture
    def tool_schema_dict(self):
        return {
            "description": "Test Tool Description",
            "parameters": [
                {"name": "param1", "type": "string", "description": "Param 1"},
                {"name": "param2", "type": "integer", "description": "Param 2"},
            ],
        }

    @pytest.fixture
    def auth_tool_schema_dict(self):
        return {
            "description": "Test Tool Description",
            "authRequired": ["test-auth-source"],
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "Param 1",
                    "authSources": ["test-auth-source"],
                },
                {"name": "param2", "type": "integer", "description": "Param 2"},
            ],
        }

    def _create_core_tool_from_dict(
        self, session, name, schema_dict, url, initial_auth_getters=None
    ):
        core_params_schemas = [
            CoreParameterSchema(**p) for p in schema_dict["parameters"]
        ]

        tool_constructor_params = []
        required_authn_for_core = {}
        for p_schema in core_params_schemas:
            if p_schema.authSources:
                required_authn_for_core[p_schema.name] = p_schema.authSources
            else:
                tool_constructor_params.append(p_schema)

        return ToolboxCoreTool(
            session=session,
            base_url=url,
            name=name,
            description=schema_dict["description"],
            params=tool_constructor_params,
            required_authn_params=types.MappingProxyType(required_authn_for_core),
            required_authz_tokens=schema_dict.get("authRequired", []),
            auth_service_token_getters=types.MappingProxyType(
                initial_auth_getters or {}
            ),
            bound_params=types.MappingProxyType({}),
            client_headers=types.MappingProxyType({}),
        )

    @pytest_asyncio.fixture
    @patch("aiohttp.ClientSession")
    async def toolbox_tool(self, MockClientSession, tool_schema_dict):
        mock_session = MockClientSession.return_value
        mock_response = mock_session.post.return_value.__aenter__.return_value
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"result": "test-result"})
        mock_response.status = 200  # *** Fix: Set status for the mock response ***

        core_tool_instance = self._create_core_tool_from_dict(
            session=mock_session,
            name="test_tool",
            schema_dict=tool_schema_dict,
            url="http://test_url",
        )
        tool = AsyncToolboxTool(core_tool=core_tool_instance)
        return tool

    @pytest_asyncio.fixture
    @patch("aiohttp.ClientSession")
    async def auth_toolbox_tool(self, MockClientSession, auth_tool_schema_dict):
        mock_session = MockClientSession.return_value
        mock_response = mock_session.post.return_value.__aenter__.return_value
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(return_value={"result": "test-result"})
        mock_response.status = 200  # *** Fix: Set status for the mock response ***

        core_tool_instance = self._create_core_tool_from_dict(
            session=mock_session,
            name="test_tool",
            schema_dict=auth_tool_schema_dict,
            url="https://test-url",
        )
        tool = AsyncToolboxTool(core_tool=core_tool_instance)
        return tool

    @patch("aiohttp.ClientSession")
    async def test_toolbox_tool_init(self, MockClientSession, tool_schema_dict):
        mock_session = MockClientSession.return_value
        mock_response = mock_session.post.return_value.__aenter__.return_value
        mock_response.status = 200
        core_tool_instance = self._create_core_tool_from_dict(
            session=mock_session,
            name="test_tool",
            schema_dict=tool_schema_dict,
            url="https://test-url",
        )
        tool = AsyncToolboxTool(core_tool=core_tool_instance)
        assert tool.metadata.name == "test_tool"
        assert tool.metadata.description == core_tool_instance.__doc__

    @pytest.mark.parametrize(
        "params_to_bind",
        [
            ({"param1": "bound-value"}),
            ({"param1": lambda: "bound-value"}),
            ({"param1": "bound-value", "param2": 123}),
        ],
    )
    async def test_toolbox_tool_bind_params(self, toolbox_tool, params_to_bind):
        original_core_tool = toolbox_tool._AsyncToolboxTool__core_tool
        with patch.object(
            original_core_tool, "bind_params", wraps=original_core_tool.bind_params
        ) as mock_core_bind_params:
            new_llamaindex_tool = toolbox_tool.bind_params(params_to_bind)
            mock_core_bind_params.assert_called_once_with(params_to_bind)
            assert isinstance(
                new_llamaindex_tool._AsyncToolboxTool__core_tool, ToolboxCoreTool
            )
            new_core_tool_signature_params = (
                new_llamaindex_tool._AsyncToolboxTool__core_tool.__signature__.parameters
            )
            for bound_param_name in params_to_bind.keys():
                assert bound_param_name not in new_core_tool_signature_params

    async def test_toolbox_tool_bind_params_invalid(self, toolbox_tool):
        with pytest.raises(
            ValueError, match="unable to bind parameters: no parameter named param3"
        ):
            toolbox_tool.bind_params({"param3": "bound-value"})

    async def test_toolbox_tool_bind_params_duplicate(self, toolbox_tool):
        tool = toolbox_tool.bind_params({"param1": "bound-value"})
        with pytest.raises(
            ValueError,
            match="cannot re-bind parameter: parameter 'param1' is already bound",
        ):
            tool.bind_params({"param1": "bound-value"})

    async def test_toolbox_tool_bind_params_invalid_params(self, auth_toolbox_tool):
        auth_core_tool = auth_toolbox_tool._AsyncToolboxTool__core_tool
        # Verify that 'param1' is not in the list of bindable parameters for the core tool
        # because it requires authentication.
        assert "param1" not in [p.name for p in auth_core_tool._ToolboxTool__params]
        with pytest.raises(
            ValueError, match="unable to bind parameters: no parameter named param1"
        ):
            auth_toolbox_tool.bind_params({"param1": "bound-value"})

    async def test_toolbox_tool_add_valid_auth_token_getter(self, auth_toolbox_tool):
        get_token_lambda = lambda: "test-token-value"
        original_core_tool = auth_toolbox_tool._AsyncToolboxTool__core_tool
        with patch.object(
            original_core_tool,
            "add_auth_token_getters",
            wraps=original_core_tool.add_auth_token_getters,
        ) as mock_core_add_getters:
            tool = auth_toolbox_tool.add_auth_token_getters(
                {"test-auth-source": get_token_lambda}
            )
            mock_core_add_getters.assert_called_once_with(
                {"test-auth-source": get_token_lambda}
            )
            core_tool_after_add = tool._AsyncToolboxTool__core_tool
            assert (
                "test-auth-source"
                in core_tool_after_add._ToolboxTool__auth_service_token_getters
            )
            assert (
                core_tool_after_add._ToolboxTool__auth_service_token_getters[
                    "test-auth-source"
                ]
                is get_token_lambda
            )
            assert not core_tool_after_add._ToolboxTool__required_authn_params.get(
                "param1"
            )
            assert (
                "test-auth-source"
                not in core_tool_after_add._ToolboxTool__required_authz_tokens
            )

    async def test_toolbox_tool_add_unused_auth_token_getter_raises_error(
        self, auth_toolbox_tool
    ):
        unused_lambda = lambda: "another-token"
        with pytest.raises(ValueError) as excinfo:
            auth_toolbox_tool.add_auth_token_getters(
                {"another-auth-source": unused_lambda}
            )
        assert (
            "Authentication source(s) `another-auth-source` unused by tool `test_tool`"
            in str(excinfo.value)
        )

        valid_lambda = lambda: "test-token"
        with pytest.raises(ValueError) as excinfo_mixed:
            auth_toolbox_tool.add_auth_token_getters(
                {
                    "test-auth-source": valid_lambda,
                    "another-auth-source": unused_lambda,
                }
            )
        assert (
            "Authentication source(s) `another-auth-source` unused by tool `test_tool`"
            in str(excinfo_mixed.value)
        )

    async def test_toolbox_tool_add_auth_token_getters_duplicate(
        self, auth_toolbox_tool
    ):
        tool = auth_toolbox_tool.add_auth_token_getters(
            {"test-auth-source": lambda: "test-token"}
        )
        with pytest.raises(
            ValueError,
            match="Authentication source\\(s\\) `test-auth-source` already registered in tool `test_tool`\\.",
        ):
            tool.add_auth_token_getters({"test-auth-source": lambda: "test-token"})

    async def test_toolbox_tool_call_requires_auth_strict(self, auth_toolbox_tool):
        with pytest.raises(
            PermissionError,
            match="One or more of the following authn services are required to invoke this tool: test-auth-source",
        ):
            await auth_toolbox_tool.acall(param2=123)

    async def test_toolbox_tool_call(self, toolbox_tool):
        result = await toolbox_tool.acall(param1="test-value", param2=123)
        assert result == ToolOutput(
            content="test-result",
            tool_name="test_tool",
            raw_input={"param1": "test-value", "param2": 123},
            raw_output="test-result",
            is_error=False,
        )

        core_tool = toolbox_tool._AsyncToolboxTool__core_tool
        core_tool._ToolboxTool__session.post.assert_called_once_with(
            "http://test_url/api/tool/test_tool/invoke",
            json={"param1": "test-value", "param2": 123},
            headers={},
        )

    @pytest.mark.parametrize(
        "bound_param_map, expected_value",
        [
            ({"param1": "bound-value"}, "bound-value"),
            ({"param1": lambda: "dynamic-value"}, "dynamic-value"),
        ],
    )
    async def test_toolbox_tool_call_with_bound_params(
        self, toolbox_tool, bound_param_map, expected_value
    ):
        tool = toolbox_tool.bind_params(bound_param_map)
        result = await tool.acall(param2=123)
        assert result == ToolOutput(
            content="test-result",
            tool_name="test_tool",
            raw_input={"param2": 123},
            raw_output="test-result",
            is_error=False,
        )
        core_tool = tool._AsyncToolboxTool__core_tool
        core_tool._ToolboxTool__session.post.assert_called_once_with(
            "http://test_url/api/tool/test_tool/invoke",
            json={"param1": expected_value, "param2": 123},
            headers={},
        )

    async def test_toolbox_tool_call_with_auth_tokens(self, auth_toolbox_tool):
        tool = auth_toolbox_tool.add_auth_token_getters(
            {"test-auth-source": lambda: "test-token"}
        )
        result = await tool.acall(param2=123)
        assert result == ToolOutput(
            content="test-result",
            tool_name="test_tool",
            raw_input={"param2": 123},
            raw_output="test-result",
            is_error=False,
        )

        core_tool = tool._AsyncToolboxTool__core_tool
        core_tool._ToolboxTool__session.post.assert_called_once_with(
            "https://test-url/api/tool/test_tool/invoke",
            json={"param2": 123},
            headers={"test-auth-source_token": "test-token"},
        )

    async def test_toolbox_tool_call_with_auth_tokens_insecure(
        self, auth_toolbox_tool, auth_tool_schema_dict
    ):
        core_tool_of_auth_tool = auth_toolbox_tool._AsyncToolboxTool__core_tool
        mock_session = core_tool_of_auth_tool._ToolboxTool__session

        with pytest.warns(
            UserWarning,
            match="Sending ID token over HTTP. User data may be exposed. Use HTTPS for secure communication.",
        ):
            insecure_core_tool = self._create_core_tool_from_dict(
                session=mock_session,
                name="test_tool",
                schema_dict=auth_tool_schema_dict,
                url="http://test-url",
            )

        insecure_auth_langchain_tool = AsyncToolboxTool(core_tool=insecure_core_tool)

        tool_with_getter = insecure_auth_langchain_tool.add_auth_token_getters(
            {"test-auth-source": lambda: "test-token"}
        )
        result = await tool_with_getter.acall(param2=123)
        assert result == ToolOutput(
            content="test-result",
            tool_name="test_tool",
            raw_input={"param2": 123},
            raw_output="test-result",
            is_error=False,
        )

        modified_core_tool_in_new_tool = tool_with_getter._AsyncToolboxTool__core_tool
        assert (
            modified_core_tool_in_new_tool._ToolboxTool__base_url == "http://test-url"
        )
        assert (
            modified_core_tool_in_new_tool._ToolboxTool__url
            == "http://test-url/api/tool/test_tool/invoke"
        )

        modified_core_tool_in_new_tool._ToolboxTool__session.post.assert_called_once_with(
            "http://test-url/api/tool/test_tool/invoke",
            json={"param2": 123},
            headers={"test-auth-source_token": "test-token"},
        )

    async def test_toolbox_tool_call_with_empty_input(self, toolbox_tool):
        with pytest.raises(TypeError) as e:
            await toolbox_tool.acall()
        assert "missing a required argument: 'param1'" in str(e.value)

    async def test_toolbox_tool_call_with_invalid_input(self, toolbox_tool):
        with pytest.raises(ValidationError) as e:
            await toolbox_tool.acall(param1=123, param2="invalid")
        assert "2 validation errors for test_tool" in str(e.value)
        assert "param1\n  Input should be a valid string" in str(e.value)
        assert "param2\n  Input should be a valid integer" in str(e.value)

    async def test_toolbox_tool_run_not_implemented(self, toolbox_tool):
        with pytest.raises(NotImplementedError):
            toolbox_tool.call()
