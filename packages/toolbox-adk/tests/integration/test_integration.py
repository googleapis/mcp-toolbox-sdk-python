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


import os
from typing import Any, Optional
from inspect import signature, Parameter
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.tools.base_tool import BaseTool

from toolbox_adk import CredentialStrategy, ToolboxTool, ToolboxToolset, ToolboxContext

# Ensure TOOLBOX_VERSION is set for the fixture
if "TOOLBOX_VERSION" not in os.environ:
    os.environ["TOOLBOX_VERSION"] = "0.0.1"  # Use a valid version or mock


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestToolboxAdkIntegration:
    """
    Integration tests reusing the toolbox_server fixture from conftest.py
    but going through the ToolboxToolset wrapper.
    """

    async def test_load_toolset_and_run(self):
        # Auth: TOOLBOX_IDENTITY for simplicity in this local test as we don't have ADK identity setup.

        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            credentials=CredentialStrategy.toolbox_identity(),
        )

        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0

            # Find 'get-row-by-id'
            tool = next((t for t in tools if t.name == "get-row-by-id"), None)
            assert tool is not None
            assert isinstance(tool, ToolboxTool)

            # Run it
            ctx = MagicMock()
            result = await tool.run_async({"id": "1"}, ctx)

            assert "row1" in result

        finally:
            await toolset.close()

    async def test_partial_loading_by_names(self):
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) == 1
            assert tools[0].name == "get-n-rows"

            # Run it
            ctx = MagicMock()
            result = await tools[0].run_async({"num_rows": "1"}, ctx)
            assert "row1" in result

        finally:
            await toolset.close()

    async def test_bound_params_e2e(self):
        # Test binding param at toolset level
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            bound_params={"num_rows": "2"},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            # Run without args, should use bound param
            ctx = MagicMock()
            result = await tools[0].run_async({}, ctx)
            assert "row2" in result
        finally:
            await toolset.close()

    async def test_3lo_flow_simulation(self):
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            # Load a specific tool that we know the arguments for
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.user_identity(
                client_id="test-client-id", client_secret="test-client-secret"
            ),
        )

        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0

            # Pick the tool
            tool = tools[0]
            assert isinstance(tool, ToolboxTool)
            assert tool.name == "get-n-rows"

            # Create a mock context that behaves like ADK's ReadonlyContext
            mock_ctx_first = MagicMock()
            # Simulate "No Auth Response Found"
            mock_ctx_first.get_auth_response.return_value = None

            print("Running tool first time (expecting auth request)...")
            result_first = await tool.run_async({"num_rows": "1"}, mock_ctx_first)

            # The wrapper should catch the missing creds and request them.
            assert (
                result_first is None
            ), "Tool should return None to signal auth requirement"
            mock_ctx_first.request_credential.assert_called_once()

            # Inspect the requested config
            auth_config = mock_ctx_first.request_credential.call_args[0][0]
            assert auth_config.raw_auth_credential.oauth2.client_id == "test-client-id"

            mock_ctx_second = MagicMock()

            # Simulate "Auth Response Found"
            mock_creds = AuthCredential(
                auth_type=AuthCredentialTypes.OAUTH2,
                oauth2=OAuth2Auth(access_token="fake-access-token"),
            )
            mock_ctx_second.get_auth_response.return_value = mock_creds

            print("Running tool second time (expecting success or server error)...")

            try:
                result_second = await tool.run_async({"num_rows": "1"}, mock_ctx_second)
                assert result_second is not None
            except Exception as e:
                mock_ctx_second.request_credential.assert_not_called()
                err_msg = str(e).lower()
                assert any(x in err_msg for x in ["401", "403", "unauthorized", "forbidden"]), f"Caught UNEXPECTED exception: {type(e).__name__}: {e}"
                print(f"Caught expected server exception with fake token: {e}")

        finally:
            await toolset.close()

    async def test_manual_token_integration(self):
        """Test the MANUAL_TOKEN strategy."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            credentials=CredentialStrategy.manual_token(token="fake-manual-token"),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0
            assert isinstance(tools[0], ToolboxTool)

        finally:
            await toolset.close()

    async def test_manual_credentials_integration(self):
        """Test the MANUAL_CREDS strategy with a mock credential object."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "fake-creds-token"

        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            credentials=CredentialStrategy.manual_credentials(credentials=mock_creds),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0
        finally:
            await toolset.close()

    async def test_header_collision(self):
        """Test that CredentialStrategy overwrites passed Authorization headers."""
        # 1. Pass explicit header
        # 2. Pass CredentialStrategy that generates a header
        # 3. Strategy should win.

        manual_override = "Bearer manual-override"
        creds_token = "Bearer strategy-token"

        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            additional_headers={"Authorization": manual_override},
            credentials=CredentialStrategy.manual_token(token="strategy-token"),
        )

        # Accessing private member for verification
        auth_header = toolset._client._core_client_headers.get("Authorization")

        assert auth_header == creds_token, "CredentialStrategy MUST overwrite additional_headers['Authorization']"

        await toolset.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestBasicE2E:
    @pytest.mark.parametrize(
        "toolset_name, expected_length, expected_tools",
        [
            ("my-toolset", 1, ["get-row-by-id"]),
            ("my-toolset-2", 2, ["get-n-rows", "get-row-by-id"]),
        ],
    )
    async def test_load_toolset_specific(
        self,
        toolset_name: str,
        expected_length: int,
        expected_tools: list[str],
    ):
        """Load a specific toolset"""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name=toolset_name,
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) == expected_length
            tool_names = {tool.name for tool in tools}
            assert tool_names == set(expected_tools)
        finally:
            await toolset.close()

    async def test_load_toolset_default(self):
        """Load the default toolset, i.e. all tools."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) == 7
            tool_names = {tool.name for tool in tools}
            expected_tools = [
                "get-row-by-content-auth",
                "get-row-by-email-auth",
                "get-row-by-id-auth",
                "get-row-by-id",
                "get-n-rows",
                "search-rows",
                "process-data",
            ]
            assert tool_names == set(expected_tools)
        finally:
            await toolset.close()

    async def test_run_tool(self):
        """Invoke a tool."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            assert isinstance(tool, ToolboxTool)

            ctx = MagicMock()
            response = await tool.run_async({"num_rows": "2"}, ctx)

            assert isinstance(response, str)
            assert "row1" in response
            assert "row2" in response
            assert "row3" not in response
        finally:
            await toolset.close()

    async def test_run_tool_missing_params(self):
        """Invoke a tool with missing params."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]

            ctx = MagicMock()
            with pytest.raises(TypeError, match="missing a required argument: 'num_rows'"):
                 await tool.run_async({}, ctx)
        finally:
            await toolset.close()

    async def test_run_tool_wrong_param_type(self):
        """Invoke a tool with wrong param type."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]

            ctx = MagicMock()
            with pytest.raises(
                ValidationError,
                match=r"num_rows\s+Input should be a valid string\s+\[type=string_type,\s+input_value=2,\s+input_type=int\]",
            ):
                await tool.run_async({"num_rows": 2}, ctx)
        finally:
            await toolset.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestBindParams:
    async def test_bind_params(self):
        """Bind a param to an existing tool."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            bound_params={"num_rows": "3"},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]

            ctx = MagicMock()
            response = await tool.run_async({}, ctx)
            assert isinstance(response, str)
            assert "row1" in response
            assert "row2" in response
            assert "row3" in response
            assert "row4" not in response
        finally:
            await toolset.close()

    async def test_bind_params_callable(self):
        """Bind a callable param to an existing tool."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            bound_params={"num_rows": lambda: "3"},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]

            ctx = MagicMock()
            response = await tool.run_async({}, ctx)
            assert isinstance(response, str)
            assert "row1" in response
            assert "row2" in response
            assert "row3" in response
            assert "row4" not in response
        finally:
            await toolset.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestAuth:
    async def test_run_tool_unauth_with_auth(self, auth_token2: str):
        """Tests running a tool that doesn't require auth, with auth provided."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-row-by-id"],
            auth_token_getters={"my-test-auth": lambda: auth_token2},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            with pytest.raises(
                ValueError,
                match=rf"Validation failed for tool 'get-row-by-id': unused auth tokens: my-test-auth",
            ):
                await toolset.get_tools()
        finally:
            await toolset.close()

    async def test_run_tool_no_auth(self):
        """Tests running a tool requiring auth without providing auth."""
        # Note: We load it without auth getters. Invocation should fail.
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-row-by-id-auth"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            with pytest.raises(
                PermissionError,
                match="One or more of the following authn services are required to invoke this tool: my-test-auth",
            ):
                await tool.run_async({"id": "2"}, ctx)
        finally:
            await toolset.close()

    async def test_run_tool_wrong_auth(self, auth_token2: str):
        """Tests running a tool with incorrect auth."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-row-by-id-auth"],
            auth_token_getters={"my-test-auth": lambda: auth_token2},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            with pytest.raises(
                Exception,
                match="tool invocation not authorized",
            ):
                await tool.run_async({"id": "2"}, ctx)
        finally:
            await toolset.close()

    async def test_run_tool_auth(self, auth_token1: str):
        """Tests running a tool with correct auth."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-row-by-id-auth"],
            auth_token_getters={"my-test-auth": lambda: auth_token1},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            response = await tool.run_async({"id": "2"}, ctx)
            assert "row2" in response
        finally:
            await toolset.close()

    async def test_run_tool_async_auth(self, auth_token1: str):
        """Tests running a tool with correct auth using an async token getter."""
        async def get_token_asynchronously():
            return auth_token1

        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-row-by-id-auth"],
            auth_token_getters={"my-test-auth": get_token_asynchronously},
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            response = await tool.run_async({"id": "2"}, ctx)
            assert "row2" in response
        finally:
            await toolset.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestOptionalParams:
    """
    End-to-end tests for tools with optional parameters.
    """

    async def test_run_tool_with_optional_params_omitted(self):
        """Invoke a tool providing only the required parameter."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["search-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            response = await tool.run_async({"email": "twishabansal@google.com"}, ctx)
            assert isinstance(response, str)
            assert '"email":"twishabansal@google.com"' in response
            assert "row2" in response
        finally:
            await toolset.close()

    async def test_run_tool_with_all_valid_params(self):
        """Invoke a tool providing all parameters."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["search-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            response = await tool.run_async({"email": "twishabansal@google.com", "id": 3, "data": "row3"}, ctx)
            assert '"email":"twishabansal@google.com"' in response
            assert "row3" in response
        finally:
            await toolset.close()

    async def test_run_tool_with_missing_required_param(self):
        """Invoke a tool without its required parameter."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["search-rows"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            with pytest.raises(TypeError, match="missing a required argument: 'email'"):
                await tool.run_async({"id": 5, "data": "row5"}, ctx)
        finally:
            await toolset.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("toolbox_server")
class TestMapParams:
    """
    End-to-end tests for tools with map parameters.
    """

    async def test_run_tool_with_map_params(self):
        """Invoke a tool with valid map parameters."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["process-data"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            # ToolboxTool.run_async takes dicts directly
            response = await tool.run_async({
                "execution_context": {"env": "prod", "id": 1234, "user": 1234.5},
                "user_scores": {"user1": 100, "user2": 200},
                "feature_flags": {"new_feature": True},
            }, ctx)

            assert isinstance(response, str)
            assert '"execution_context":{"env":"prod","id":1234,"user":1234.5}' in response
            assert '"user_scores":{"user1":100,"user2":200}' in response
            assert '"feature_flags":{"new_feature":true}' in response
        finally:
            await toolset.close()

    async def test_run_tool_with_wrong_map_value_type(self):
        """Invoke a tool with a map parameter having the wrong value type."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["process-data"],
            credentials=CredentialStrategy.toolbox_identity(),
        )
        try:
            tools = await toolset.get_tools()
            tool = tools[0]
            ctx = MagicMock()

            with pytest.raises(ValidationError):
                await tool.run_async({
                    "execution_context": {"env": "staging"},
                    "user_scores": {"user4": "not-an-integer"},
                }, ctx)
        finally:
            await toolset.close()
