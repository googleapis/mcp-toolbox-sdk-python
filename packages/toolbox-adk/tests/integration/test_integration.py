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


import os
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)

from toolbox_adk import CredentialStrategy, ToolboxTool, ToolboxToolset

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
            credentials=CredentialStrategy.TOOLBOX_IDENTITY(),
        )

        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0

            # Find 'get-row-by-id'
            tool = next((t for t in tools if t.name == "get-row-by-id"), None)
            assert tool is not None
            assert isinstance(tool, ToolboxTool)

            # Run it
            # Mocking ToolContext as we are running directly
            ctx = MagicMock()
            result = await tool.run_async({"id": "1"}, ctx)

            assert "row1" in result

        finally:
            await toolset.close()

    async def test_partial_loading_by_names(self):
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            tool_names=["get-n-rows"],
            credentials=CredentialStrategy.TOOLBOX_IDENTITY(),
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
            credentials=CredentialStrategy.TOOLBOX_IDENTITY(),
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
            # We use an existing toolset that contains auth tools or just any toolset if we can pick specific tools
            toolset_name="my-toolset",
            credentials=CredentialStrategy.USER_IDENTITY(
                client_id="test-client-id", client_secret="test-client-secret"
            ),
        )

        try:
            # We filter for a simple tool if possible, or just take the first one.
            tools = await toolset.get_tools()
            assert len(tools) > 0

            # Pick a tool
            tool = tools[0]
            assert isinstance(tool, ToolboxTool)

            # Create a mock context that behaves like ADK's ReadonlyContext
            mock_ctx_first = MagicMock()
            # Simulate "No Auth Response Found"
            mock_ctx_first.get_auth_response.return_value = None

            print("Running tool first time (expecting auth request)...")
            result_first = await tool.run_async({}, mock_ctx_first)

            # The wrapper should catch the missing creds and request them.
            assert (
                result_first is None
            ), "Tool should return None to signal auth requirement"
            mock_ctx_first.request_credential.assert_called_once()

            # Inspect the requested config
            auth_config = mock_ctx_first.request_credential.call_args[0][0]
            assert auth_config.raw_auth_credential.oauth2.client_id == "test-client-id"

            # The runner would get the token. We simulate passing it back in context.
            mock_ctx_second = MagicMock()

            # Simulate "Auth Response Found"
            mock_creds = AuthCredential(
                auth_type=AuthCredentialTypes.OAUTH2,
                oauth2=OAuth2Auth(access_token="fake-access-token"),
            )
            mock_ctx_second.get_auth_response.return_value = mock_creds

            print("Running tool second time (expecting success or server error)...")

            try:
                result_second = await tool.run_async({}, mock_ctx_second)
                assert result_second is not None
            except Exception as e:
                # If it fails, strictly it's likely a 401 or similar from the backend interactions.
                # This confirms the wrapper proceeded to call the backend and did NOT request credentials again.
                mock_ctx_second.request_credential.assert_not_called()
                print(f"Caught expected server exception with fake token: {e}")

        finally:
            await toolset.close()

    async def test_manual_token_integration(self):
        """Test the MANUAL_TOKEN strategy."""
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            credentials=CredentialStrategy.MANUAL_TOKEN(token="fake-manual-token"),
        )
        try:
            tools = await toolset.get_tools()
            assert len(tools) > 0
            assert isinstance(tools[0], ToolboxTool)

        finally:
            await toolset.close()

    async def test_manual_creds_integration(self):
        """Test the MANUAL_CREDS strategy with a mock credential object."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "fake-creds-token"
        
        toolset = ToolboxToolset(
            server_url="http://localhost:5000",
            toolset_name="my-toolset",
            credentials=CredentialStrategy.MANUAL_CREDS(credentials=mock_creds),
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
            credentials=CredentialStrategy.MANUAL_TOKEN(token="strategy-token"),
        )
        
        # We need to inspect the client to see what it chose.
        # Accessing private member for verification
        auth_header = toolset._client._core_client_headers.get("Authorization")
        
        assert auth_header == creds_token, "CredentialStrategy MUST overwrite additional_headers['Authorization']"
        
        await toolset.close()
