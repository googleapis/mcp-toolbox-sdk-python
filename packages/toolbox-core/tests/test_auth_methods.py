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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from toolbox_core import auth_methods

# Constants for test values
MOCK_GOOGLE_ID_TOKEN = "test_id_token_123"
MOCK_PROJECT_ID = "test-project"
# A realistic expiry timestamp (e.g., 1 hour from now)
MOCK_EXPIRY_TIMESTAMP = time.time() + 3600

# Expected exception messages from auth_methods.py
FETCH_TOKEN_FAILURE_MSG = "Failed to fetch Google ID token."
FETCH_ASYNC_TOKEN_FAILURE_MSG = "Failed to fetch async Google ID token."
# These will now match the actual messages from refresh.side_effect
NETWORK_ERROR_MSG = "Network error"
TIMEOUT_ERROR_MSG = "Timeout error"


@pytest.fixture(autouse=True)
def reset_cache_after_each_test():
    """Fixture to reset the cache before each test."""
    # Store initial state
    original_cache_state = auth_methods._cached_google_id_token.copy()
    auth_methods._cached_google_id_token = {"token": None, "expires_at": 0}
    yield
    # Restore initial state (optional, but good for isolation)
    auth_methods._cached_google_id_token = original_cache_state


class TestAsyncAuthMethods:
    """Tests for asynchronous Google ID token fetching."""

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_success_first_call(
        self, mock_default_async, mock_async_req_class, mock_decode_expiry
    ):
        """Tests successful fetching of an async token on the first call."""
        mock_creds_instance = AsyncMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN
        mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = MOCK_EXPIRY_TIMESTAMP

        mock_async_req_instance = MagicMock()
        mock_async_req_class.return_value = mock_async_req_instance

        token = await auth_methods.aget_google_id_token()

        mock_default_async.assert_called_once_with()
        mock_async_req_class.assert_called_once_with()
        mock_creds_instance.refresh.assert_called_once_with(mock_async_req_instance)

        assert (
            mock_creds_instance.before_request.func
            is auth_methods.Credentials.before_request
        )
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == MOCK_EXPIRY_TIMESTAMP
        )
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_success_uses_cache(
        self, mock_default_async, mock_async_req_class, mock_decode_expiry
    ):
        """Tests that subsequent calls use the cached token if valid."""
        auth_methods._cached_google_id_token["token"] = MOCK_GOOGLE_ID_TOKEN
        auth_methods._cached_google_id_token["expires_at"] = (
            time.time() + auth_methods.CACHE_REFRESH_MARGIN_SECONDS + 100
        )  # Ensure it's valid

        token = await auth_methods.aget_google_id_token()

        mock_default_async.assert_not_called()
        mock_async_req_class.assert_not_called()
        mock_decode_expiry.assert_not_called()

        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_refreshes_expired_cache(
        self, mock_default_async, mock_async_req_class, mock_decode_expiry
    ):
        """Tests that an expired cached token triggers a refresh."""
        auth_methods._cached_google_id_token["token"] = "expired_token"
        auth_methods._cached_google_id_token["expires_at"] = (
            time.time() - 100
        )  # Expired

        mock_creds_instance = AsyncMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN  # New token after refresh
        mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = MOCK_EXPIRY_TIMESTAMP

        mock_async_req_instance = MagicMock()
        mock_async_req_class.return_value = mock_async_req_instance

        token = await auth_methods.aget_google_id_token()

        mock_default_async.assert_called_once_with()
        mock_async_req_class.assert_called_once_with()
        mock_creds_instance.refresh.assert_called_once_with(mock_async_req_instance)
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == MOCK_EXPIRY_TIMESTAMP
        )
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_fetch_failure(
        self, mock_default_async, mock_async_req_class
    ):
        """Tests error handling when fetching the token fails (no id_token returned)."""
        mock_creds_instance = AsyncMock()
        mock_creds_instance.id_token = None  # Simulate no ID token after refresh
        mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_async_req_class.return_value = MagicMock()

        with pytest.raises(Exception, match=FETCH_ASYNC_TOKEN_FAILURE_MSG):
            await auth_methods.aget_google_id_token()

        assert auth_methods._cached_google_id_token["token"] is None
        assert auth_methods._cached_google_id_token["expires_at"] == 0
        mock_async_req_class.assert_called_once_with()
        mock_creds_instance.refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_refresh_raises_exception(
        self, mock_default_async, mock_async_req_class
    ):
        """Tests exception handling when credentials refresh fails."""
        mock_creds_instance = AsyncMock()
        mock_creds_instance.refresh.side_effect = Exception(NETWORK_ERROR_MSG)
        mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_async_req_class.return_value = MagicMock()

        with pytest.raises(Exception, match=NETWORK_ERROR_MSG):
            await auth_methods.aget_google_id_token()

        assert auth_methods._cached_google_id_token["token"] is None
        assert auth_methods._cached_google_id_token["expires_at"] == 0
        mock_async_req_class.assert_called_once_with()
        mock_creds_instance.refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods._aiohttp_requests.Request")
    @patch("toolbox_core.auth_methods.default_async", new_callable=MagicMock)
    async def test_aget_google_id_token_no_expiry_info(
        self, mock_default_async, mock_async_req_class, mock_decode_expiry
    ):
        """Tests that a token without expiry info is still cached but effectively expired."""
        mock_creds_instance = AsyncMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN
        mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = None  # Simulate no expiry info

        mock_async_req_class.return_value = MagicMock()

        token = await auth_methods.aget_google_id_token()

        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == 0
        )  # Should be 0 if no expiry
        mock_async_req_class.assert_called_once_with()
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)


class TestSyncAuthMethods:
    """Tests for synchronous Google ID token fetching."""

    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_success_first_call(
        self,
        mock_sync_default,
        mock_auth_session_class,
        mock_sync_req_class,
        mock_decode_expiry,
    ):
        """Tests successful fetching of a sync token on the first call."""
        mock_creds_instance = MagicMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN
        mock_sync_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = MOCK_EXPIRY_TIMESTAMP

        mock_session_instance = MagicMock()
        mock_auth_session_class.return_value = mock_session_instance

        mock_sync_request_instance = MagicMock()
        mock_sync_req_class.return_value = mock_sync_request_instance

        token = auth_methods.get_google_id_token()

        mock_sync_default.assert_called_once_with()
        mock_auth_session_class.assert_called_once_with(mock_creds_instance)
        mock_sync_req_class.assert_called_once_with(mock_session_instance)
        mock_creds_instance.refresh.assert_called_once_with(mock_sync_request_instance)

        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == MOCK_EXPIRY_TIMESTAMP
        )
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)

    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_success_uses_cache(
        self,
        mock_sync_default,
        mock_auth_session_class,
        mock_sync_req_class,
        mock_decode_expiry,
    ):
        """Tests that subsequent calls use the cached token if valid."""
        auth_methods._cached_google_id_token["token"] = MOCK_GOOGLE_ID_TOKEN
        auth_methods._cached_google_id_token["expires_at"] = (
            time.time() + auth_methods.CACHE_REFRESH_MARGIN_SECONDS + 100
        )  # Ensure it's valid

        token = auth_methods.get_google_id_token()

        mock_sync_default.assert_not_called()
        mock_auth_session_class.assert_not_called()
        mock_sync_req_class.assert_not_called()
        mock_decode_expiry.assert_not_called()

        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN

    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_refreshes_expired_cache(
        self,
        mock_sync_default,
        mock_auth_session_class,
        mock_sync_req_class,
        mock_decode_expiry,
    ):
        """Tests that an expired cached token triggers a refresh."""
        # Prime the cache with an expired token
        auth_methods._cached_google_id_token["token"] = "expired_token_sync"
        auth_methods._cached_google_id_token["expires_at"] = (
            time.time() - 100
        )  # Expired

        mock_creds_instance = MagicMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN  # New token after refresh
        mock_sync_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = MOCK_EXPIRY_TIMESTAMP

        mock_session_instance = MagicMock()
        mock_auth_session_class.return_value = mock_session_instance

        mock_sync_request_instance = MagicMock()
        mock_sync_req_class.return_value = mock_sync_request_instance

        token = auth_methods.get_google_id_token()

        mock_sync_default.assert_called_once_with()
        mock_auth_session_class.assert_called_once_with(mock_creds_instance)
        mock_sync_req_class.assert_called_once_with(mock_session_instance)
        mock_creds_instance.refresh.assert_called_once_with(mock_sync_request_instance)
        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == MOCK_EXPIRY_TIMESTAMP
        )
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)

    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_fetch_failure(
        self, mock_sync_default, mock_auth_session_class, mock_sync_req_class
    ):
        """Tests error handling when fetching the token fails (no id_token returned)."""
        mock_creds_instance = MagicMock()
        mock_creds_instance.id_token = None  # Simulate no ID token after refresh
        mock_sync_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

        mock_session_instance = MagicMock()
        mock_auth_session_class.return_value = mock_session_instance

        mock_sync_req_class.return_value = MagicMock()

        with pytest.raises(Exception, match=FETCH_TOKEN_FAILURE_MSG):
            auth_methods.get_google_id_token()

        assert auth_methods._cached_google_id_token["token"] is None
        assert auth_methods._cached_google_id_token["expires_at"] == 0
        mock_sync_default.assert_called_once_with()
        mock_auth_session_class.assert_called_once_with(mock_creds_instance)
        mock_sync_req_class.assert_called_once_with(mock_session_instance)
        mock_creds_instance.refresh.assert_called_once()

    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_refresh_raises_exception(
        self, mock_sync_default, mock_auth_session_class, mock_sync_req_class
    ):
        """Tests exception handling when credentials refresh fails."""
        mock_creds_instance = MagicMock()
        mock_creds_instance.refresh.side_effect = Exception(TIMEOUT_ERROR_MSG)
        mock_sync_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

        mock_session_instance = MagicMock()
        mock_auth_session_class.return_value = mock_session_instance

        mock_sync_req_class.return_value = MagicMock()

        with pytest.raises(Exception, match=TIMEOUT_ERROR_MSG):
            auth_methods.get_google_id_token()

        assert auth_methods._cached_google_id_token["token"] is None
        assert auth_methods._cached_google_id_token["expires_at"] == 0
        mock_sync_default.assert_called_once_with()
        mock_auth_session_class.assert_called_once_with(mock_creds_instance)
        mock_sync_req_class.assert_called_once_with(mock_session_instance)
        mock_creds_instance.refresh.assert_called_once()

    @patch("toolbox_core.auth_methods._decode_jwt_and_get_expiry")
    @patch("toolbox_core.auth_methods.Request")
    @patch("toolbox_core.auth_methods.AuthorizedSession")
    @patch("toolbox_core.auth_methods.google.auth.default")
    def test_get_google_id_token_no_expiry_info(
        self,
        mock_sync_default,
        mock_auth_session_class,
        mock_sync_req_class,
        mock_decode_expiry,
    ):
        """Tests that a token without expiry info is still cached but effectively expired."""
        mock_creds_instance = MagicMock()
        mock_creds_instance.id_token = MOCK_GOOGLE_ID_TOKEN
        mock_sync_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)
        mock_decode_expiry.return_value = None  # Simulate no expiry info

        mock_session_instance = MagicMock()
        mock_auth_session_class.return_value = mock_session_instance

        mock_sync_request_instance = MagicMock()
        mock_sync_req_class.return_value = mock_sync_request_instance

        token = auth_methods.get_google_id_token()

        assert token == f"{auth_methods.BEARER_TOKEN_PREFIX}{MOCK_GOOGLE_ID_TOKEN}"
        assert auth_methods._cached_google_id_token["token"] == MOCK_GOOGLE_ID_TOKEN
        assert (
            auth_methods._cached_google_id_token["expires_at"] == 0
        )  # Should be 0 if no expiry
        mock_sync_default.assert_called_once_with()
        mock_auth_session_class.assert_called_once_with(mock_creds_instance)
        mock_sync_req_class.assert_called_once_with(mock_session_instance)
        mock_decode_expiry.assert_called_once_with(MOCK_GOOGLE_ID_TOKEN)
