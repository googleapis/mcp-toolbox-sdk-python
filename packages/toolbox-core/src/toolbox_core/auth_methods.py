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

"""
This module provides functions to obtain Google ID tokens for a specific audience.

The tokens are returned as "Bearer" strings for direct use in HTTP Authorization
headers. It uses a simple in-memory cache to avoid refetching on every call.

Example Usage:
from toolbox_core import auth_methods

URL = "https://toolbox-service-url"
async with ToolboxClient(
    URL,
    client_headers={"Authorization": auth_methods.aget_google_id_token})
as toolbox:
    tools = await toolbox.load_toolset()
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import id_token

# --- Constants ---
BEARER_TOKEN_PREFIX = "Bearer "
CACHE_REFRESH_MARGIN = timedelta(seconds=60)
DEFAULT_CLOCK_SKEW = 0

_token_cache: Dict[str, Any] = {
    "token": None,
    "expires_at": datetime.min.replace(tzinfo=timezone.utc),
}


def _is_token_valid() -> bool:
    """Checks if the cached token exists and is not nearing expiry."""
    if not _token_cache["token"]:
        return False
    return datetime.now(timezone.utc) < (
        _token_cache["expires_at"] - CACHE_REFRESH_MARGIN
    )


def _update_cache(new_token: str, clock_skew_in_seconds: int) -> None:
    """
    Validates a new token, extracts its expiry, and updates the cache.

    Args:
        new_token: The new JWT ID token string.

    Raises:
        ValueError: If the token is invalid or its expiry cannot be determined.
    """
    try:
        # verify_oauth2_token not only decodes but also validates the token's
        # signature and claims against Google's public keys.
        # It's a synchronous, CPU-bound operation, safe for async contexts.
        claims = id_token.verify_oauth2_token(
            new_token, Request(), clock_skew_in_seconds=clock_skew_in_seconds
        )

        expiry_timestamp = claims.get("exp")
        if not expiry_timestamp:
            raise ValueError("Token does not contain an 'exp' claim.")

        _token_cache["token"] = new_token
        _token_cache["expires_at"] = datetime.fromtimestamp(
            expiry_timestamp, tz=timezone.utc
        )

    except (ValueError, GoogleAuthError) as e:
        # Clear cache on failure to prevent using a stale or invalid token
        _token_cache["token"] = None
        _token_cache["expires_at"] = datetime.min.replace(tzinfo=timezone.utc)
        raise ValueError(f"Failed to validate and cache the new token: {e}") from e


def get_google_token_from_aud(
    clock_skew_in_seconds: int = 0, audience: Optional[str] = None
) -> str:
    if clock_skew_in_seconds < 0 or clock_skew_in_seconds > 60:
        raise ValueError(
            f"Illegal clock_skew_in_seconds value: {clock_skew_in_seconds}. Must be between 0 and 60"
            ", inclusive."
        )

    if _is_token_valid():
        return BEARER_TOKEN_PREFIX + _token_cache["token"]

    # Get local user credentials
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)
    credentials.refresh(request)

    if hasattr(credentials, "id_token"):
        new_id_token = getattr(credentials, "id_token", None)
        if new_id_token:
            _update_cache(new_id_token, clock_skew_in_seconds)
            return BEARER_TOKEN_PREFIX + new_id_token

    if audience is None:
        raise Exception(
            "You are not authenticating using User Credentials."
            " Please set the audience string to the Toolbox service URL to get the Google ID token."
        )

    # Get credentials for Google Cloud environments or for service account key files
    try:
        request = Request()
        new_token = id_token.fetch_id_token(request, audience)
        _update_cache(new_token, clock_skew_in_seconds)
        return BEARER_TOKEN_PREFIX + _token_cache["token"]

    except GoogleAuthError as e:
        raise GoogleAuthError(
            f"Failed to fetch Google ID token for audience '{audience}': {e}"
        ) from e


def get_google_id_token(
    audience: Optional[str] = None, clock_skew_in_seconds: int = DEFAULT_CLOCK_SKEW
) -> Callable[[], str]:
    """
    Returns a SYNC function that, when called, fetches a Google ID token.
    This function uses Application Default Credentials for local systems
    and standard google auth libraries for Google Cloud environments.
    It caches the token in memory.

    Args:
        audience: The audience for the ID token (e.g., a service URL or client
        ID).
        clock_skew_in_seconds: The number of seconds to tolerate when checking the token.
            Must be between 0-60. Defaults to 0.

    Returns:
        A function that when executed returns string in the format "Bearer <google_id_token>".

    Raises:
        GoogleAuthError: If fetching credentials or the token fails.
        ValueError: If the fetched token is invalid.
    """

    def _token_getter() -> str:
        return get_google_token_from_aud(clock_skew_in_seconds, audience)

    return _token_getter


def aget_google_id_token(
    audience: Optional[str] = None, clock_skew_in_seconds: int = DEFAULT_CLOCK_SKEW
) -> Callable[[], Coroutine[Any, Any, str]]:
    """
    Returns an ASYNC function that, when called, fetches a Google ID token.
    This function uses Application Default Credentials for local systems
    and standard google auth libraries for Google Cloud environments.
    It caches the token in memory.

    Args:
        audience: The audience for the ID token (e.g., a service URL or client
        ID).
        clock_skew_in_seconds: The number of seconds to tolerate when checking the token.
            Must be between 0-60. Defaults to 0.

    Returns:
        An async function that when executed returns string in the format "Bearer <google_id_token>".

    Raises:
        GoogleAuthError: If fetching credentials or the token fails.
        ValueError: If the fetched token is invalid.
    """

    async def _token_getter() -> str:
        return await asyncio.to_thread(
            get_google_token_from_aud, clock_skew_in_seconds, audience
        )

    return _token_getter
