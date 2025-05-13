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

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import google.auth.exceptions

from toolbox_core import auth_methods

# Constants for test values
MOCK_ASYNC_ID_TOKEN = "test_async_id_token_123"
MOCK_SYNC_ID_TOKEN = "test_sync_id_token_456"
MOCK_PROJECT_ID = "test-project"

# Error Messages
ADC_NOT_FOUND_MSG = "ADC not found"
TOKEN_REFRESH_FAILED_MSG = "Token refresh failed"
SYNC_ADC_NOT_FOUND_MSG = "Sync ADC not found"
SYNC_TOKEN_REFRESH_FAILED_MSG = "Sync token refresh failed"


@pytest.mark.asyncio
@patch("toolbox_core.auth_methods.partial")
@patch("toolbox_core.auth_methods._aiohttp_requests.Request")
@patch("toolbox_core.auth_methods.Credentials")
@patch("toolbox_core.auth_methods.default_async")
async def test_aget_google_id_token_success(
    mock_default_async,
    mock_credentials_class,
    mock_aiohttp_request_class,
    mock_partial,
):
    """
    Test aget_google_id_token successfully retrieves and formats a token.
    """
    mock_creds_instance = AsyncMock()
    mock_creds_instance.id_token = MOCK_ASYNC_ID_TOKEN
    mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

    mock_aio_request_instance = MagicMock()
    mock_aiohttp_request_class.return_value = mock_aio_request_instance

    mock_unbound_before_request = MagicMock()
    mock_credentials_class.before_request = mock_unbound_before_request

    mock_partial_object = MagicMock()
    mock_partial.return_value = mock_partial_object

    token = await auth_methods.aget_google_id_token()

    mock_default_async.assert_called_once_with()
    mock_aiohttp_request_class.assert_called_once_with()
    mock_creds_instance.refresh.assert_called_once_with(mock_aio_request_instance)

    mock_partial.assert_called_once_with(
        mock_unbound_before_request, mock_creds_instance
    )
    assert mock_creds_instance.before_request == mock_partial_object
    assert token == f"Bearer {MOCK_ASYNC_ID_TOKEN}"


@pytest.mark.asyncio
@patch("toolbox_core.auth_methods.default_async")
async def test_aget_google_id_token_default_credentials_error(mock_default_async):
    """
    Test aget_google_id_token handles DefaultCredentialsError.
    """
    mock_default_async.side_effect = google.auth.exceptions.DefaultCredentialsError(
        ADC_NOT_FOUND_MSG
    )

    with pytest.raises(
        google.auth.exceptions.DefaultCredentialsError, match=ADC_NOT_FOUND_MSG
    ):
        await auth_methods.aget_google_id_token()

    mock_default_async.assert_called_once_with()


@pytest.mark.asyncio
@patch("toolbox_core.auth_methods._aiohttp_requests.Request")
@patch("toolbox_core.auth_methods.default_async")
async def test_aget_google_id_token_refresh_error(
    mock_default_async,
    mock_aiohttp_request_class,
):
    """
    Test aget_google_id_token handles RefreshError.
    """
    mock_creds_instance = AsyncMock()
    mock_creds_instance.refresh.side_effect = google.auth.exceptions.RefreshError(
        TOKEN_REFRESH_FAILED_MSG
    )
    mock_default_async.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

    mock_aio_request_instance = MagicMock()
    mock_aiohttp_request_class.return_value = mock_aio_request_instance

    with pytest.raises(
        google.auth.exceptions.RefreshError, match=TOKEN_REFRESH_FAILED_MSG
    ):
        await auth_methods.aget_google_id_token()

    mock_default_async.assert_called_once_with()
    mock_aiohttp_request_class.assert_called_once_with()
    mock_creds_instance.refresh.assert_called_once_with(mock_aio_request_instance)


# --- Synchronous Tests ---

@patch("toolbox_core.auth_methods.Request")
@patch("toolbox_core.auth_methods.AuthorizedSession")
@patch("toolbox_core.auth_methods.google.auth.default")
def test_get_google_id_token_success(
    mock_google_auth_default,
    mock_authorized_session_class,
    mock_request_class,
):
    """
    Test get_google_id_token successfully retrieves and formats a token.
    """
    mock_creds_instance = MagicMock()
    mock_creds_instance.id_token = MOCK_SYNC_ID_TOKEN
    mock_google_auth_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

    mock_session_instance = MagicMock()
    mock_authorized_session_class.return_value = mock_session_instance

    mock_request_instance = MagicMock()
    mock_request_class.return_value = mock_request_instance

    token = auth_methods.get_google_id_token()

    mock_google_auth_default.assert_called_once_with()
    mock_authorized_session_class.assert_called_once_with(mock_creds_instance)
    mock_request_class.assert_called_once_with(mock_session_instance)
    mock_creds_instance.refresh.assert_called_once_with(mock_request_instance)
    assert token == f"Bearer {MOCK_SYNC_ID_TOKEN}"


@patch("toolbox_core.auth_methods.google.auth.default")
def test_get_google_id_token_default_credentials_error(mock_google_auth_default):
    """
    Test get_google_id_token handles DefaultCredentialsError.
    """
    mock_google_auth_default.side_effect = (
        google.auth.exceptions.DefaultCredentialsError(SYNC_ADC_NOT_FOUND_MSG)
    )

    with pytest.raises(
        google.auth.exceptions.DefaultCredentialsError, match=SYNC_ADC_NOT_FOUND_MSG
    ):
        auth_methods.get_google_id_token()

    mock_google_auth_default.assert_called_once_with()


@patch("toolbox_core.auth_methods.Request")
@patch("toolbox_core.auth_methods.AuthorizedSession")
@patch("toolbox_core.auth_methods.google.auth.default")
def test_get_google_id_token_refresh_error(
    mock_google_auth_default,
    mock_authorized_session_class,
    mock_request_class,
):
    """
    Test get_google_id_token handles RefreshError.
    """
    mock_creds_instance = MagicMock()
    mock_creds_instance.refresh.side_effect = google.auth.exceptions.RefreshError(
        SYNC_TOKEN_REFRESH_FAILED_MSG
    )
    mock_google_auth_default.return_value = (mock_creds_instance, MOCK_PROJECT_ID)

    mock_session_instance = MagicMock()
    mock_authorized_session_class.return_value = mock_session_instance

    mock_request_instance = MagicMock()
    mock_request_class.return_value = mock_request_instance

    with pytest.raises(
        google.auth.exceptions.RefreshError, match=SYNC_TOKEN_REFRESH_FAILED_MSG
    ):
        auth_methods.get_google_id_token()

    mock_google_auth_default.assert_called_once_with()
    mock_authorized_session_class.assert_called_once_with(mock_creds_instance)
    mock_request_class.assert_called_once_with(mock_session_instance)
    mock_creds_instance.refresh.assert_called_once_with(mock_request_instance)