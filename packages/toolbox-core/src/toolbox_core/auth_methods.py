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
This module provides functions to obtain Google ID tokens, formatted as "Bearer" tokens,
for use in the "Authorization" header of HTTP requests.

Example User Experience:
from toolbox_core import auth_methods

auth_token_provider = auth_methods.aget_google_id_token
toolbox = ToolboxClient(
    URL,
    client_headers={"Authorization": auth_token_provider},
)
tools = await toolbox.load_toolset()
"""

import time
from functools import partial
from typing import Any, Dict, Optional

import google.auth
import jwt
from google.auth._credentials_async import Credentials
from google.auth._default_async import default_async
from google.auth.transport import _aiohttp_requests
from google.auth.transport.requests import AuthorizedSession, Request

# --- Constants and Configuration ---
# Prefix for Authorization header tokens
BEARER_TOKEN_PREFIX = "Bearer "
# Margin in seconds to refresh token before its actual expiry
CACHE_REFRESH_MARGIN_SECONDS = 60


# --- Global Cache Storage ---
# Stores the cached Google ID token and its expiry timestamp
_cached_google_id_token: Dict[str, Any] = {"token": None, "expires_at": 0}


# --- Helper Functions ---
def _decode_jwt_and_get_expiry(id_token: str) -> Optional[float]:
    """
    Decodes a JWT and extracts the 'exp' (expiration) claim.

    Args:
        id_token: The JWT string to decode.

    Returns:
        The 'exp' timestamp as a float if present and decoding is successful,
        otherwise None.
    """
    try:
        decoded_token = jwt.decode(
            id_token, options={"verify_signature": False, "verify_aud": False}
        )
        return decoded_token.get("exp")
    except jwt.PyJWTError:
        return None


def _is_cached_token_valid(
    cache: Dict[str, Any], margin_seconds: int = CACHE_REFRESH_MARGIN_SECONDS
) -> bool:
    """
    Checks if a token in the cache is valid (exists and not expired).

    Args:
        cache: The dictionary containing 'token' and 'expires_at'.
        margin_seconds: The time in seconds before expiry to consider the token invalid.

    Returns:
        True if the token is valid, False otherwise.
    """
    if not cache.get("token"):
        return False

    expires_at = cache.get("expires_at")
    if not isinstance(expires_at, (int, float)) or expires_at <= 0:
        return False

    return time.time() < (expires_at - margin_seconds)


def _update_token_cache(cache: Dict[str, Any], new_id_token: Optional[str]) -> None:
    """
    Updates the global token cache with a new token and its expiry.

    Args:
        cache: The dictionary containing 'token' and 'expires_at'.
        new_id_token: The new ID token string to cache.
    """
    if new_id_token:
        cache["token"] = new_id_token
        expiry_timestamp = _decode_jwt_and_get_expiry(new_id_token)
        if expiry_timestamp:
            cache["expires_at"] = expiry_timestamp
        else:
            # If expiry can't be determined, treat as immediately expired to force refresh
            cache["expires_at"] = 0
    else:
        # Clear cache if no new token is provided
        cache["token"] = None
        cache["expires_at"] = 0


# --- Public API Functions ---
def get_google_id_token() -> str:
    """
    Synchronously fetches a Google ID token.

    The token is formatted as a 'Bearer' token string and is suitable for use
    in an HTTP Authorization header. This function uses Application Default
    Credentials.

    Returns:
        A string in the format "Bearer <google_id_token>".

    Raises:
        Exception: If fetching the Google ID token fails.
    """
    if _is_cached_token_valid(_cached_google_id_token):
        return BEARER_TOKEN_PREFIX + _cached_google_id_token["token"]

    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)
    credentials.refresh(request)
    new_id_token = getattr(credentials, "id_token", None)

    _update_token_cache(_cached_google_id_token, new_id_token)
    if new_id_token:
        return BEARER_TOKEN_PREFIX + new_id_token
    else:
        raise Exception("Failed to fetch Google ID token.")


async def aget_google_id_token() -> str:
    """
    Asynchronously fetches a Google ID token.

    The token is formatted as a 'Bearer' token string and is suitable for use
    in an HTTP Authorization header. This function uses Application Default
    Credentials.

    Returns:
        A string in the format "Bearer <google_id_token>".

    Raises:
        Exception: If fetching the Google ID token fails.
    """
    if _is_cached_token_valid(_cached_google_id_token):
        return BEARER_TOKEN_PREFIX + _cached_google_id_token["token"]

    credentials, _ = default_async()
    await credentials.refresh(_aiohttp_requests.Request())
    credentials.before_request = partial(Credentials.before_request, credentials)
    new_id_token = getattr(credentials, "id_token", None)

    _update_token_cache(_cached_google_id_token, new_id_token)

    if new_id_token:
        return BEARER_TOKEN_PREFIX + new_id_token
    else:
        raise Exception("Failed to fetch async Google ID token.")
