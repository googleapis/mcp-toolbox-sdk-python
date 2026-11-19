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

import time
import unittest
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from google.auth.exceptions import GoogleAuthError
from toolbox_core import auth_methods

from toolbox_adk import CredentialStrategy, ToolboxClient
from toolbox_adk.client import CredentialConfig, CredentialType


@pytest.fixture(autouse=True)
def reset_id_token_cache():
    """Isolates tests from the toolbox-core ID token cache (keyed by audience)."""
    original_cache = auth_methods._token_cache.copy()
    auth_methods._token_cache.clear()
    yield
    auth_methods._token_cache.clear()
    auth_methods._token_cache.update(original_cache)


@pytest.mark.asyncio
class TestToolboxClientAuth:
    """Unit tests for Client Auth logic."""

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_toolbox_identity(self, mock_core_client):
        """Test init with TOOLBOX_IDENTITY (no auth headers)."""
        creds = CredentialStrategy.toolbox_identity()
        client = ToolboxClient(server_url="http://test", credentials=creds)

        # Verify core client created with empty headers for auth
        _, kwargs = mock_core_client.call_args
        assert "client_headers" in kwargs
        headers = kwargs["client_headers"]
        assert "Authorization" not in headers
        assert kwargs["client_name"] == "toolbox-adk-python"
        assert kwargs["client_version"] is not None

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    @patch("toolbox_adk.client.auth_methods.get_google_id_token")
    async def test_init_adc_delegates_to_core_id_token_getter(
        self, mock_get_id_token, mock_core_client
    ):
        """Test ADC strategy uses the toolbox-core ID token getter for the audience."""
        core_getter = MagicMock(return_value="Bearer id-token-123")
        mock_get_id_token.return_value = core_getter

        creds = CredentialStrategy.application_default_credentials(
            target_audience="aud"
        )
        ToolboxClient(server_url="http://test", credentials=creds)

        mock_get_id_token.assert_called_once_with("aud")
        headers = mock_core_client.call_args[1]["client_headers"]
        assert headers["Authorization"] is core_getter
        assert headers["Authorization"]() == "Bearer id-token-123"

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch("toolbox_core.auth_methods.google.auth.default")
    async def test_init_adc_success_fetch_id_token(
        self, mock_default, mock_fetch_id, mock_verify, mock_core_client
    ):
        """Test ADC strategy where an audience-bound ID token can be fetched."""
        mock_default.return_value = (MagicMock(id_token=None), "proj")
        mock_fetch_id.return_value = "id-token-123"
        mock_verify.return_value = {"exp": int(time.time()) + 3600}

        creds = CredentialStrategy.application_default_credentials(
            target_audience="aud"
        )
        ToolboxClient(server_url="http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        assert token_getter() == "Bearer id-token-123"
        mock_fetch_id.assert_called_once_with(ANY, "aud")

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch("toolbox_core.auth_methods.google.auth.default")
    async def test_init_adc_local_user_credentials_id_token(
        self, mock_default, mock_fetch_id, mock_verify, mock_core_client
    ):
        """Test ADC strategy with local user credentials that carry an ID token."""
        mock_default.return_value = (MagicMock(id_token="user-id-token"), "proj")
        mock_verify.return_value = {"exp": int(time.time()) + 3600}

        creds = CredentialStrategy.application_default_credentials(
            target_audience="aud"
        )
        ToolboxClient(server_url="http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        assert token_getter() == "Bearer user-id-token"
        mock_fetch_id.assert_not_called()

    @pytest.mark.parametrize(
        "access_token",
        ["fake-access-token-123", None],
        ids=["access_token_present", "no_token"],
    )
    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch("toolbox_core.auth_methods.google.auth.default")
    async def test_init_adc_never_falls_back_to_access_token(
        self, mock_default, mock_fetch_id, mock_core_client, access_token
    ):
        """Test ADC strategy raises instead of sending an OAuth2 access token."""
        mock_creds = MagicMock(id_token=None, token=access_token)
        mock_default.return_value = (mock_creds, "proj")
        mock_fetch_id.side_effect = GoogleAuthError("No metadata server")

        creds = CredentialStrategy.application_default_credentials(
            target_audience="aud"
        )
        ToolboxClient(server_url="http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        with pytest.raises(GoogleAuthError, match="No metadata server"):
            token_getter()

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_api_key(self, mock_core_client):
        creds = CredentialStrategy.api_key(key="123", header_name="x-foo")
        client = ToolboxClient("http://test", credentials=creds)
        headers = mock_core_client.call_args[1]["client_headers"]
        assert headers["x-foo"] == "123"
        assert "Authorization" not in headers

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_manual_token(self, mock_core_client):
        creds = CredentialStrategy.manual_token(token="abc")
        client = ToolboxClient("http://test", credentials=creds)
        headers = mock_core_client.call_args[1]["client_headers"]
        assert headers["Authorization"] == "Bearer abc"

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_manual_credentials(self, mock_core_client):
        mock_google_creds = MagicMock()
        mock_google_creds.valid = True
        mock_google_creds.token = "creds-token"

        creds = CredentialStrategy.manual_credentials(credentials=mock_google_creds)
        client = ToolboxClient("http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        assert token_getter() == "Bearer creds-token"

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_manual_credentials_refresh(self, mock_core_client):
        """Test MANUAL_CREDS refreshes if invalid."""
        mock_google_creds = MagicMock()
        mock_google_creds.valid = False
        mock_google_creds.token = "refreshed-token"

        creds = CredentialStrategy.manual_credentials(credentials=mock_google_creds)
        client = ToolboxClient("http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        assert token_getter() == "Bearer refreshed-token"
        mock_google_creds.refresh.assert_called_once()

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_init_user_identity(self, mock_core_client):
        creds = CredentialStrategy.user_identity(client_id="c", client_secret="s")
        client = ToolboxClient("http://test", credentials=creds)

        token_getter = mock_core_client.call_args[1]["client_headers"]["Authorization"]
        # Should be empty initially
        assert token_getter() == ""

        # Set context
        from toolbox_adk.client import USER_TOKEN_CONTEXT_VAR

        token = USER_TOKEN_CONTEXT_VAR.set("user-tok")
        try:
            assert token_getter() == "Bearer user-tok"
        finally:
            USER_TOKEN_CONTEXT_VAR.reset(token)

    async def test_validation_errors(self):
        with pytest.raises(
            ValueError, match="target_audience is required for WORKLOAD_IDENTITY"
        ):
            # WORKLOAD_IDENTITY requires audience
            creds = CredentialStrategy.workload_identity(target_audience="")
            ToolboxClient("http://test", credentials=creds)

        with pytest.raises(ValueError):
            creds = CredentialStrategy.manual_token(token="")
            ToolboxClient("http://test", credentials=creds)

        with pytest.raises(ValueError):
            creds = CredentialStrategy.manual_credentials(credentials=None)
            ToolboxClient("http://test", credentials=creds)

        with pytest.raises(
            ValueError, match="api_key and header_name are required for API_KEY"
        ):
            # Manually constructing invalid config since factory enforces signature
            creds = CredentialConfig(
                type=CredentialType.API_KEY, api_key=None, header_name=None
            )
            ToolboxClient("http://test", credentials=creds)

    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_load_methods(self, mock_core_client_class):
        # Setup mock instance
        mock_instance = AsyncMock()
        mock_core_client_class.return_value = mock_instance

        client = ToolboxClient(
            "http://test", credentials=CredentialStrategy.toolbox_identity()
        )

        # Test load_toolset
        await client.load_toolset("ts", foo="bar")
        mock_instance.load_toolset.assert_called_with("ts", foo="bar")

        # Test load_tool
        await client.load_tool("t", baz="qux")
        mock_instance.load_tool.assert_called_with("t", baz="qux")

        # Test close
        await client.close()
        mock_instance.close.assert_called_once()

        # Test property
        assert client.credential_config is not None

    @pytest.mark.parametrize(
        "telemetry_enabled",
        [False, True],
        ids=["telemetry_disabled", "telemetry_enabled"],
    )
    @patch("toolbox_adk.client.toolbox_core.ToolboxClient")
    async def test_telemetry_enabled_forwarded(
        self, mock_core_client, telemetry_enabled
    ):
        """Verifies that telemetry_enabled is forwarded to the core client."""
        ToolboxClient(server_url="http://test", telemetry_enabled=telemetry_enabled)
        call_kwargs = mock_core_client.call_args[1]
        assert call_kwargs["telemetry_enabled"] == telemetry_enabled
