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
from functools import partial

auth_token_provider = functools.partial(
    auth_methods.aget_google_id_token,
    "https://toolbox-service-url"
)
client = ToolboxClient(URL, client_headers={"Authorization": auth_token_provider})
await client.make_request()
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import google.auth
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request, AuthorizedSession
from google.oauth2 import id_token
import asyncio

# --- Constants ---
BEARER_TOKEN_PREFIX = "Bearer "
CACHE_REFRESH_MARGIN = timedelta(seconds=60)

_token_cache: Dict[str, Any] = {"token": None, "expires_at": datetime.min.replace(tzinfo=timezone.utc)}

def _is_token_valid() -> bool:
    """Checks if the cached token exists and is not nearing expiry."""
    if not _token_cache["token"]:
        return False
    return datetime.now(timezone.utc) < (_token_cache["expires_at"] - CACHE_REFRESH_MARGIN)

def _update_cache(new_token: str) -> None:
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
        claims = id_token.verify_oauth2_token(new_token, Request())
        
        expiry_timestamp = claims.get("exp")
        if not expiry_timestamp:
            raise ValueError("Token does not contain an 'exp' claim.")
            
        _token_cache["token"] = new_token
        _token_cache["expires_at"] = datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc)

    except (ValueError, GoogleAuthError) as e:
        # Clear cache on failure to prevent using a stale or invalid token
        _token_cache["token"] = None
        _token_cache["expires_at"] = datetime.min.replace(tzinfo=timezone.utc)
        raise ValueError(f"Failed to validate and cache the new token: {e}") from e


# --- Public API Functions ---

def get_google_id_token(audience: str) -> str:
    """
    Synchronously fetches a Google ID token for a specific audience.

    This function uses Application Default Credentials and caches the token in memory.

    Args:
        audience: The audience for the ID token (e.g., a service URL or client ID).

    Returns:
        A string in the format "Bearer <google_id_token>".

    Raises:
        GoogleAuthError: If fetching credentials or the token fails.
        ValueError: If the fetched token is invalid.
    """
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
            _update_cache(new_id_token)
            return BEARER_TOKEN_PREFIX + new_id_token

    # Get credentials for Google Cloud environments
    try:
        request = Request()
        new_token = id_token.fetch_id_token(request, audience)
        _update_cache(new_token)
        return BEARER_TOKEN_PREFIX + _token_cache["token"]
        
    except GoogleAuthError as e:
        raise GoogleAuthError(f"Failed to fetch Google ID token for audience '{audience}': {e}") from e
    
async def aget_google_id_token(audience: str) -> str:
    token = await asyncio.to_thread(get_google_id_token, audience) 
    return token