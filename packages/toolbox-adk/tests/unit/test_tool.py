# Copyright 2026 Google LLC
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

from unittest.mock import AsyncMock, MagicMock

import pytest

from toolbox_adk.credentials import CredentialConfig, CredentialType
from toolbox_adk.tool import ToolboxTool


class TestToolboxTool:

    @pytest.mark.asyncio
    async def test_run_async_passthrough(self):
        mock_core = AsyncMock()
        mock_core.__name__ = "my_tool"
        mock_core.__doc__ = "my description"
        mock_core.return_value = "success"

        tool = ToolboxTool(mock_core)

        assert tool.name == "my_tool"

        ctx = MagicMock()
        result = await tool.run_async({"arg": 1}, ctx)

        assert result == "success"
        mock_core.assert_awaited_with(arg=1)

    @pytest.mark.asyncio
    async def test_hooks(self):
        mock_core = AsyncMock(return_value="res")
        mock_core.__name__ = "hooked_tool"
        mock_core.__doc__ = "hooked description"

        async def before(ctx, args):
            args["arg"] += 1

        async def after(ctx, args, result, error):
            assert result == "res"
            # Verify we can see the modified arg
            assert args["arg"] == 2

        tool = ToolboxTool(mock_core, pre_hook=before, post_hook=after)

        result = await tool.run_async({"arg": 1}, MagicMock())

        mock_core.assert_awaited_with(arg=2)
        assert result == "res"

    @pytest.mark.asyncio
    async def test_error_in_hook(self):
        mock_core = AsyncMock()
        mock_core.__name__ = "mock"
        mock_core.__doc__ = "mock"

        async def failing_hook(ctx, args):
            raise ValueError("Boom")

        tool = ToolboxTool(mock_core, pre_hook=failing_hook)

        with pytest.raises(ValueError, match="Boom"):
            await tool.run_async({}, MagicMock())

        mock_core.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_async_exception_handling(self):
        mock_core = AsyncMock(side_effect=ValueError("Execution failed"))
        mock_core.__name__ = "mock"
        mock_core.__doc__ = "mock"
        tool = ToolboxTool(mock_core)

        ctx = MagicMock()

        # We expect the error to be re-raised
        with pytest.raises(ValueError, match="Execution failed"):
            await tool.run_async({}, ctx)

        # ctx.error is set but local to run_async. Verified via post_hook in next test.

    @pytest.mark.asyncio
    async def test_run_async_exception_captured_in_hook(self):
        # Allow verifying ctx.error via post_hook
        mock_core = AsyncMock(side_effect=ValueError("Fail"))
        mock_core.__name__ = "mock"
        mock_core.__doc__ = "mock"

        captured_error = None

        async def after(ctx, args, result, error):
            nonlocal captured_error
            captured_error = error

        tool = ToolboxTool(mock_core, post_hook=after)

        with pytest.raises(ValueError, match="Fail"):
            await tool.run_async({}, MagicMock())

        assert isinstance(captured_error, ValueError)
        assert str(captured_error) == "Fail"

    @pytest.mark.asyncio
    async def test_auth_check_no_token(self):
        # Scenario: ADK context has no token initially
        mock_core = AsyncMock(return_value="ok")
        mock_core.__name__ = "mock"
        mock_core.__doc__ = "mock"
        tool = ToolboxTool(mock_core)

        ctx = MagicMock()
        ctx.get_auth_response.return_value = None

        await tool.run_async({}, ctx)

        # Should proceed to execute (auth not forced)
        mock_core.assert_awaited()

    @pytest.mark.asyncio
    async def test_bind_params(self):
        mock_core = MagicMock()
        mock_core.__name__ = "mock"
        mock_core.__doc__ = "mock"
        
        # return_value must be an object with metadata
        new_core_mock = MagicMock()
        new_core_mock.__name__ = "bound_mock"
        new_core_mock.__doc__ = "bound mock"
        mock_core.bind_params.return_value = new_core_mock

        tool = ToolboxTool(mock_core, pre_hook=None)
        new_tool = tool.bind_params({"a": 1})

        assert isinstance(new_tool, ToolboxTool)
        # Note: Mocked string return prevents full type verification.
        assert new_tool._core_tool == new_core_mock
        mock_core.bind_params.assert_called_with({"a": 1})

    @pytest.mark.asyncio
    async def test_3lo_missing_client_secret(self):
        # Test ValueError when client_id/secret missing
        core_tool = AsyncMock()
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"
        auth_config = CredentialConfig(type=CredentialType.USER_IDENTITY)
        # Missing client_id/secret

        tool = ToolboxTool(core_tool, auth_config=auth_config)
        ctx = MagicMock()  # Mock the context

        with pytest.raises(
            ValueError, match="USER_IDENTITY requires client_id and client_secret"
        ):
            await tool.run_async({"arg": "val"}, ctx)

    @pytest.mark.asyncio
    async def test_3lo_request_credential_when_missing(self):
        # Test that if creds are missing, request_credential is called and returns None
        core_tool = AsyncMock()
        core_tool.__name__ = "mock"
        core_tool.__doc__ = "mock"
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"

        auth_config = CredentialConfig(
            type=CredentialType.USER_IDENTITY, client_id="cid", client_secret="csec"
        )

        tool = ToolboxTool(core_tool, auth_config=auth_config)

        ctx = MagicMock()
        # Mock get_auth_response returning None (no creds yet)
        ctx.get_auth_response.return_value = None

        result = await tool.run_async({}, ctx)

        # Verify result is None (signal pause)
        assert result is None
        # Verify request_credential was called
        ctx.request_credential.assert_called_once()
        # Verify core tool was NOT called
        core_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_3lo_uses_existing_credential(self):
        # Test that if creds exist, they are used and injected
        core_tool = AsyncMock(return_value="success")
        core_tool.__name__ = "mock"
        core_tool.__doc__ = "mock"
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"

        auth_config = CredentialConfig(
            type=CredentialType.USER_IDENTITY, client_id="cid", client_secret="csec"
        )

        tool = ToolboxTool(core_tool, auth_config=auth_config)

        ctx = MagicMock()
        # Mock get_auth_response returning valid creds
        mock_creds = MagicMock()
        mock_creds.oauth2.access_token = "valid_token"
        ctx.get_auth_response.return_value = mock_creds

        result = await tool.run_async({}, ctx)

        # Verify result is success
        assert result == "success"
        # Verify request_credential was NOT called
        ctx.request_credential.assert_not_called()
        # Verify core tool WAS called
        core_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_3lo_exception_reraise(self):
        # Test that specific credential errors are re-raised
        core_tool = AsyncMock()
        core_tool.__name__ = "mock"
        core_tool.__doc__ = "mock"
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"

        auth_config = CredentialConfig(
            type=CredentialType.USER_IDENTITY, client_id="cid", client_secret="csec"
        )
        tool = ToolboxTool(core_tool, auth_config=auth_config)
        ctx = MagicMock()

        # Mock get_auth_response raising ValueError
        ctx.get_auth_response.side_effect = ValueError("Invalid Credential")

        with pytest.raises(ValueError, match="Invalid Credential"):
            await tool.run_async({}, ctx)

    @pytest.mark.asyncio
    async def test_3lo_exception_fallback(self):
        # Test that non-credential errors trigger fallback request
        core_tool = AsyncMock()
        core_tool.__name__ = "mock"
        core_tool.__doc__ = "mock"
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"

        auth_config = CredentialConfig(
            type=CredentialType.USER_IDENTITY, client_id="cid", client_secret="csec"
        )
        tool = ToolboxTool(core_tool, auth_config=auth_config)
        ctx = MagicMock()

        # Mock get_auth_response raising generic error
        ctx.get_auth_response.side_effect = RuntimeError("Random failure")

        result = await tool.run_async({}, ctx)

        # Should catch RuntimeError, call request_credential, and return None
        assert result is None
        ctx.request_credential.assert_called_once()
        
    def test_param_type_to_schema_type(self):
        core_tool = MagicMock()
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"
        tool = ToolboxTool(core_tool)
        
        from google.genai.types import Type
        assert tool._param_type_to_schema_type("string") == Type.STRING
        assert tool._param_type_to_schema_type("integer") == Type.INTEGER
        assert tool._param_type_to_schema_type("boolean") == Type.BOOLEAN
        assert tool._param_type_to_schema_type("number") == Type.NUMBER
        assert tool._param_type_to_schema_type("array") == Type.ARRAY
        assert tool._param_type_to_schema_type("object") == Type.OBJECT
        assert tool._param_type_to_schema_type("unknown") == Type.STRING

    def test_get_declaration(self):
        # Create a mock for core tool parameters
        class MockParam:
            def __init__(self, name, param_type, description, required):
                self.name = name
                self.type = param_type
                self.description = description
                self.required = required

        core_tool = MagicMock()
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"
        core_tool._params = [
            MockParam("city", "string", "The city name", True),
            MockParam("count", "integer", "Number of results", False)
        ]
        
        tool = ToolboxTool(core_tool)
        declaration = tool._get_declaration()
        
        from google.genai.types import Type
        assert declaration.name == "mock_tool"
        assert declaration.description == "mock doc"
        
        parameters = declaration.parameters
        assert parameters is not None
        assert parameters.type == Type.OBJECT
        assert "city" in parameters.properties
        assert "count" in parameters.properties
        
        assert parameters.properties["city"].type == Type.STRING
        assert parameters.properties["city"].description == "The city name"
        
        assert parameters.properties["count"].type == Type.INTEGER
        assert parameters.properties["count"].description == "Number of results"
        
        assert parameters.required == ["city"]
        
    def test_get_declaration_no_params(self):
        core_tool = MagicMock()
        core_tool.__name__ = "mock_tool"
        core_tool.__doc__ = "mock doc"
        core_tool._params = []
        
        tool = ToolboxTool(core_tool)
        declaration = tool._get_declaration()
        
        assert declaration.name == "mock_tool"
        assert declaration.description == "mock doc"
        assert getattr(declaration, "parameters", None) is None

    def test_init_defaults(self):
        # Test initialization with minimal tool metadata checks
        class EmptyTool:
            pass

        core_tool = EmptyTool()

        # Now we expect ValueError because valid metadata is enforced
        with pytest.raises(ValueError, match="must have a valid __name__"):
            ToolboxTool(core_tool)
        core_tool.__name__ = "valid_tool"
        # Still fails on doc
        with pytest.raises(ValueError, match="must have a valid __doc__"):
            ToolboxTool(core_tool)

        core_tool.__doc__ = "valid description"
        tool = ToolboxTool(core_tool)
        assert tool.name == "valid_tool"
        assert tool.description == "valid description"
