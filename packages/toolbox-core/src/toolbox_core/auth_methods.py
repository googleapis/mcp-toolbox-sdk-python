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
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

import google.auth
from google.auth import compute_engine, external_account, impersonated_credentials
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import id_token, service_account

# --- Constants ---
BEARER_TOKEN_PREFIX = "Bearer "
CACHE_REFRESH_MARGIN = timedelta(seconds=60)
DEFAULT_CLOCK_SKEW = 0

# The cache is keyed by `audience`: an ID token is scoped to a single audience
# via its `aud` claim, so a token minted for audience A must never be returned
# for a request targeting audience B (doing so would leak a credential for A to
# B and break OIDC audience isolation).
#
# A key of None is the local/user-credentials (ADC) path: the token is taken
# from the credentials' own `id_token` rather than fetched for a specific
# audience. That token's audience is fixed when the credentials are issued (not
# by a per-call value), so all audience-less calls safely share the single None
# entry and never mix with audience-specific entries.
_CacheKey = Optional[str]
_token_cache: Dict[_CacheKey, Dict[str, Any]] = {}
_token_cache_lock = threading.RLock()


def _is_token_valid(cache_key: _CacheKey) -> bool:
    """Checks if a cached token for the given key exists and is not nearing expiry."""
    with _token_cache_lock:
        entry = _token_cache.get(cache_key)
        if not entry or not entry.get("token"):
            return False
        return datetime.now(timezone.utc) < (entry["expires_at"] - CACHE_REFRESH_MARGIN)


def _update_cache(
    cache_key: _CacheKey, new_token: str, clock_skew_in_seconds: int
) -> None:
    """
    Validates a new token, extracts its expiry, and updates the cache entry for
    the given key.

    Args:
        cache_key: The audience the token was fetched for (used as the cache key).
        new_token: The new JWT ID token string.
        clock_skew_in_seconds: Leeway, in seconds, forwarded to token verification
            when validating the token's time-based claims.

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

        with _token_cache_lock:
            _token_cache[cache_key] = {
                "token": new_token,
                "expires_at": datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc),
            }

    except (ValueError, GoogleAuthError) as e:
        # Drop this key's entry on failure to prevent using a stale/invalid token
        with _token_cache_lock:
            _token_cache.pop(cache_key, None)
        raise ValueError(f"Failed to validate and cache the new token: {e}") from e


def _mint_id_token_from_default_credentials(
    credentials: Any, audience: Optional[str], fetch_err: Optional[Exception]
) -> str:
    """Mints an OIDC ID token from ADC credentials without falling back to access tokens."""
    if audience is not None:
        id_creds: Optional[Any] = None
        if isinstance(credentials, service_account.Credentials):
            id_creds = service_account.IDTokenCredentials(
                credentials._signer,
                credentials.service_account_email,
                credentials._token_uri,
                target_audience=audience,
                quota_project_id=credentials.quota_project_id,
                universe_domain=credentials.universe_domain,
            )
        elif isinstance(credentials, impersonated_credentials.Credentials):
            id_creds = impersonated_credentials.IDTokenCredentials(
                target_credentials=credentials,
                target_audience=audience,
                include_email=True,
            )
        elif isinstance(credentials, external_account.Credentials):
            if not credentials._should_initialize_impersonated_credentials():
                raise GoogleAuthError(
                    f"Failed to fetch Google ID token for audience '{audience}': "
                    "external account credentials without service account impersonation cannot mint ID tokens."
                ) from fetch_err
            id_creds = impersonated_credentials.IDTokenCredentials(
                target_credentials=credentials._initialize_impersonated_credentials(),
                target_audience=audience,
                include_email=True,
            )
        elif isinstance(credentials, compute_engine.Credentials):
            raise GoogleAuthError(
                f"Failed to fetch Google ID token for audience '{audience}': {fetch_err}"
            ) from fetch_err

        if id_creds is not None:
            id_creds.refresh(Request())
            if not id_creds.token:
                raise GoogleAuthError(
                    f"Failed to fetch Google ID token for audience '{audience}'."
                )
            return str(id_creds.token)

    if not isinstance(
        credentials,
        (
            service_account.Credentials,
            impersonated_credentials.Credentials,
            external_account.Credentials,
            compute_engine.Credentials,
        ),
    ):
        session = AuthorizedSession(credentials)
        credentials.refresh(Request(session))
        new_id_token = getattr(credentials, "id_token", None)
        if new_id_token:
            return str(new_id_token)

    if audience is None:
        raise Exception(
            "You are not authenticating using User Credentials."
            " Please set the audience string to the Toolbox service URL to get the Google ID token."
        )

    raise GoogleAuthError(
        f"Failed to fetch Google ID token for audience '{audience}': {fetch_err}"
    ) from fetch_err


def get_google_token_from_aud(
    clock_skew_in_seconds: int = 0, audience: Optional[str] = None
) -> str:
    if clock_skew_in_seconds < 0 or clock_skew_in_seconds > 60:
        raise ValueError(
            f"Illegal clock_skew_in_seconds value: {clock_skew_in_seconds}. Must be between 0 and 60"
            ", inclusive."
        )

    cache_key: _CacheKey = audience

    with _token_cache_lock:
        if _is_token_valid(cache_key):
            return BEARER_TOKEN_PREFIX + _token_cache[cache_key]["token"]

        fetch_err: Optional[GoogleAuthError] = None
        if audience is not None:
            try:
                new_token = id_token.fetch_id_token(Request(), audience)
                _update_cache(cache_key, new_token, clock_skew_in_seconds)
                return BEARER_TOKEN_PREFIX + _token_cache[cache_key]["token"]
            except GoogleAuthError as e:
                fetch_err = e

        try:
            credentials, _ = google.auth.default()
            new_token = _mint_id_token_from_default_credentials(
                credentials, audience, fetch_err
            )
        except GoogleAuthError as e:
            if audience is not None and fetch_err is not None and e is not fetch_err:
                raise GoogleAuthError(
                    f"Failed to fetch Google ID token for audience '{audience}': {e}"
                ) from e
            raise

        _update_cache(cache_key, new_token, clock_skew_in_seconds)
        return BEARER_TOKEN_PREFIX + _token_cache[cache_key]["token"]


def get_google_id_token(
    audience: Optional[str] = None, clock_skew_in_seconds: int = DEFAULT_CLOCK_SKEW
) -> Callable[[], str]:
    """
    Returns a SYNC function that, when called, fetches a Google ID token.
    This function uses Application Default Credentials for local systems
    and standard google auth libraries for Google Cloud environments.
    It caches the token in memory, keyed by audience.

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
    It caches the token in memory, keyed by audience.

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
