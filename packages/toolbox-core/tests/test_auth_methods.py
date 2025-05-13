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

import google.auth.exceptions
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from toolbox_core import auth_methods

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
    Test aget_google_id_token successfully retrieves and formats a token using pytest.
    """
    # Setup mock for default_async() -> (creds, project_id)
    mock_creds_instance = AsyncMock()
    mock_creds_instance.id_token = "test_async_id_token_123"
    mock_default_async.return_value = (mock_creds_instance, "test-project")

    # Setup mock for _aiohttp_requests.Request()
    mock_aio_request_instance = MagicMock()
    mock_aiohttp_request_class.return_value = mock_aio_request_instance

    # Setup mock for Credentials.before_request (class attribute used in partial)
    mock_unbound_before_request = MagicMock()
    mock_credentials_class.before_request = mock_unbound_before_request

    # Setup mock for partial()
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

    assert token == "Bearer test_async_id_token_123"


@pytest.mark.asyncio
@patch("toolbox_core.auth_methods.default_async")
async def test_aget_google_id_token_default_credentials_error(mock_default_async):
    """
    Test aget_google_id_token when default_async raises DefaultCredentialsError.
    """
    mock_default_async.side_effect = google.auth.exceptions.DefaultCredentialsError(
        "ADC not found"
    )

    with pytest.raises(
        google.auth.exceptions.DefaultCredentialsError, match="ADC not found"
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
    Test aget_google_id_token when creds.refresh raises RefreshError.
    The `partial` call should not happen if refresh fails.
    """
    mock_creds_instance = AsyncMock()
    mock_creds_instance.refresh.side_effect = google.auth.exceptions.RefreshError(
        "Token refresh failed"
    )
    mock_default_async.return_value = (mock_creds_instance, "test-project")

    mock_aio_request_instance = MagicMock()
    mock_aiohttp_request_class.return_value = mock_aio_request_instance

    with pytest.raises(
        google.auth.exceptions.RefreshError, match="Token refresh failed"
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
    Test get_google_id_token successfully retrieves and formats a token using pytest.
    """
    # Setup mock for google.auth.default() -> (credentials, project_id)
    mock_creds_instance = MagicMock()
    mock_creds_instance.id_token = "test_sync_id_token_456"
    mock_google_auth_default.return_value = (mock_creds_instance, "test-project")

    # Setup mock for AuthorizedSession()
    mock_session_instance = MagicMock()
    mock_authorized_session_class.return_value = mock_session_instance

    # Setup mock for Request()
    mock_request_instance = MagicMock()
    mock_request_class.return_value = mock_request_instance

    token = auth_methods.get_google_id_token()

    mock_google_auth_default.assert_called_once_with()
    mock_authorized_session_class.assert_called_once_with(mock_creds_instance)
    mock_request_class.assert_called_once_with(mock_session_instance)
    mock_creds_instance.refresh.assert_called_once_with(mock_request_instance)
    assert token == "Bearer test_sync_id_token_456"


@patch("toolbox_core.auth_methods.google.auth.default")
def test_get_google_id_token_default_credentials_error(mock_google_auth_default):
    """
    Test get_google_id_token when google.auth.default raises DefaultCredentialsError.
    """
    mock_google_auth_default.side_effect = (
        google.auth.exceptions.DefaultCredentialsError("Sync ADC not found")
    )

    with pytest.raises(
        google.auth.exceptions.DefaultCredentialsError, match="Sync ADC not found"
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
    Test get_google_id_token when credentials.refresh raises RefreshError.
    """
    mock_creds_instance = MagicMock()
    mock_creds_instance.refresh.side_effect = google.auth.exceptions.RefreshError(
        "Sync token refresh failed"
    )
    mock_google_auth_default.return_value = (mock_creds_instance, "test-project")

    mock_session_instance = MagicMock()
    mock_authorized_session_class.return_value = mock_session_instance

    mock_request_instance = MagicMock()
    mock_request_class.return_value = mock_request_instance

    with pytest.raises(
        google.auth.exceptions.RefreshError, match="Sync token refresh failed"
    ):
        auth_methods.get_google_id_token()

    mock_google_auth_default.assert_called_once_with()
    mock_authorized_session_class.assert_called_once_with(mock_creds_instance)
    mock_request_class.assert_called_once_with(mock_session_instance)
    mock_creds_instance.refresh.assert_called_once_with(mock_request_instance)