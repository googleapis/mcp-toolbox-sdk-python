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

import time
from unittest.mock import ANY, MagicMock, patch

import pytest
from google.auth.exceptions import GoogleAuthError

from toolbox_core import auth_methods

# Constants for test values
MOCK_ID_TOKEN = "test_id_token_123"
MOCK_PROJECT_ID = "test-project"
MOCK_AUDIENCE = "https://test-audience.com"
# A realistic expiry timestamp (e.g., 1 hour from now)
MOCK_EXPIRY_TIMESTAMP = int(time.time()) + 3600
MOCK_EXPIRY_DATETIME = auth_methods.datetime.fromtimestamp(
    MOCK_EXPIRY_TIMESTAMP, tz=auth_methods.timezone.utc
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Fixture to reset the module's token cache before each test."""
    original_cache = auth_methods._token_cache.copy()
    # Reset to the initial empty state as defined in the new module
    auth_methods._token_cache["token"] = None
    auth_methods._token_cache["expires_at"] = auth_methods.datetime.min.replace(
        tzinfo=auth_methods.timezone.utc
    )
    yield
    auth_methods._token_cache = original_cache


@pytest.mark.asyncio
class TestAsyncAuthMethods:
    """Tests for asynchronous Google ID token fetching."""

    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    async def test_aget_google_id_token_success_first_call(
        self, mock_default, mock_fetch, mock_verify
    ):
        """Tests successful fetching of an async token on the first call."""
        mock_fetch.return_value = MOCK_ID_TOKEN
        mock_verify.return_value = {"exp": MOCK_EXPIRY_TIMESTAMP}

        token_getter = auth_methods.aget_google_id_token(MOCK_AUDIENCE)
        token = await token_getter()

        mock_default.assert_called_once()
        mock_fetch.assert_called_once_with(ANY, MOCK_AUDIENCE)
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_ID_TOKEN}"
        assert auth_methods._token_cache["token"] == MOCK_ID_TOKEN
        assert auth_methods._token_cache["expires_at"] == MOCK_EXPIRY_DATETIME

    @patch("toolbox_core.auth_methods.google.auth.default")
    async def test_aget_google_id_token_success_uses_cache(self, mock_default):
        """Tests that subsequent calls use the cached token if valid."""
        auth_methods._token_cache["token"] = MOCK_ID_TOKEN
        auth_methods._token_cache["expires_at"] = auth_methods.datetime.now(
            auth_methods.timezone.utc
        ) + auth_methods.timedelta(hours=1)

        token_getter = auth_methods.aget_google_id_token(MOCK_AUDIENCE)
        token = await token_getter()

        mock_default.assert_not_called()
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_ID_TOKEN}"

    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    async def test_aget_google_id_token_refreshes_expired_cache(
        self, mock_default, mock_fetch, mock_verify
    ):
        """Tests that an expired cached token triggers a refresh."""
        auth_methods._token_cache["token"] = "expired_token"
        auth_methods._token_cache["expires_at"] = auth_methods.datetime.now(
            auth_methods.timezone.utc
        ) - auth_methods.timedelta(seconds=100)

        mock_fetch.return_value = MOCK_ID_TOKEN
        mock_verify.return_value = {"exp": MOCK_EXPIRY_TIMESTAMP}

        token_getter = auth_methods.aget_google_id_token(MOCK_AUDIENCE)
        token = await token_getter()

        mock_default.assert_called_once()
        mock_fetch.assert_called_once()
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_ID_TOKEN}"
        assert auth_methods._token_cache["token"] == MOCK_ID_TOKEN

    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    async def test_aget_raises_if_no_audience_and_no_local_token(
        self, mock_default, mock_fetch
    ):
        """Tests that the async function propagates the missing audience exception."""
        error_msg = "You are not authenticating using User Credentials."
        with pytest.raises(Exception, match=error_msg):
            token_getter = auth_methods.aget_google_id_token()
            await token_getter()

        mock_default.assert_called_once()
        mock_fetch.assert_not_called()


class TestSyncAuthMethods:
    """Tests for synchronous Google ID token fetching."""

    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_success_local_creds(
        self, mock_default, mock_session, mock_request, mock_verify
    ):
        """Tests successful fetching via local credentials."""
        mock_creds = MagicMock()
        mock_creds.id_token = MOCK_ID_TOKEN
        mock_default.return_value = (mock_creds, MOCK_PROJECT_ID)
        mock_verify.return_value = {"exp": MOCK_EXPIRY_TIMESTAMP}
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_request_instance = MagicMock()
        mock_request.return_value = mock_request_instance

        token_getter = auth_methods.get_google_id_token(MOCK_AUDIENCE)
        token = token_getter()

        mock_default.assert_called_once_with()
        mock_session.assert_called_once_with(mock_creds)
        mock_creds.refresh.assert_called_once_with(mock_request_instance)
        mock_verify.assert_called_once_with(MOCK_ID_TOKEN, ANY, clock_skew_in_seconds=0)
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_ID_TOKEN}"
        assert auth_methods._token_cache["token"] == MOCK_ID_TOKEN
        assert auth_methods._token_cache["expires_at"] == MOCK_EXPIRY_DATETIME

    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_success_uses_cache(self, mock_default):
        """Tests that subsequent calls use the cached token if valid."""
        auth_methods._token_cache["token"] = MOCK_ID_TOKEN
        auth_methods._token_cache["expires_at"] = auth_methods.datetime.now(
            auth_methods.timezone.utc
        ) + auth_methods.timedelta(hours=1)

        token_getter = auth_methods.get_google_id_token(MOCK_AUDIENCE)
        token = token_getter()

        mock_default.assert_not_called()
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_ID_TOKEN}"

    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    def test_get_google_id_token_fetch_failure(
        self, mock_default, mock_fetch, mock_verify
    ):
        """Tests error handling when fetching the token fails."""
        mock_fetch.side_effect = GoogleAuthError("Fetch failed")

        with pytest.raises(GoogleAuthError, match="Fetch failed"):
            auth_methods.get_google_id_token(MOCK_AUDIENCE)()

        assert auth_methods._token_cache["token"] is None
        mock_default.assert_called_once()
        mock_fetch.assert_called_once()
        mock_verify.assert_not_called()

    @patch("toolbox_core.auth_methods.id_token.verify_oauth2_token")
    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    def test_get_google_id_token_validation_failure(
        self, mock_default, mock_fetch, mock_verify
    ):
        """Tests that an invalid token from fetch raises a ValueError."""
        mock_fetch.return_value = MOCK_ID_TOKEN
        mock_verify.side_effect = ValueError("Invalid signature")

        with pytest.raises(
            ValueError, match="Failed to validate and cache the new token"
        ):
            auth_methods.get_google_id_token(MOCK_AUDIENCE)()

        assert auth_methods._token_cache["token"] is None

    @patch("toolbox_core.auth_methods.id_token.fetch_id_token")
    @patch(
        "toolbox_core.auth_methods.google.auth.default",
        return_value=(MagicMock(id_token=None), MOCK_PROJECT_ID),
    )
    def test_get_raises_if_no_audience_and_no_local_token(
        self, mock_default, mock_fetch
    ):
        """Tests exception is raised if audience is required but not provided."""
        error_msg = "You are not authenticating using User Credentials."
        with pytest.raises(Exception, match=error_msg):
            auth_methods.get_google_id_token()()

        mock_default.assert_called_once()
        mock_fetch.assert_not_called()
