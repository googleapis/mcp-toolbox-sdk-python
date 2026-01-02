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

from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, Optional, Union

import google.auth
import toolbox_core
from google.auth import compute_engine, transport
from google.auth.transport import requests
from google.oauth2 import id_token

from .credentials import CredentialConfig, CredentialType

USER_TOKEN_CONTEXT_VAR: ContextVar[Optional[str]] = ContextVar(
    "toolbox_user_token", default=None
)


class ToolboxClient:
    """
    Wraps toolbox_core.ToolboxClient to provide ADK-native authentication strategy support.
    """

    def __init__(
        self,
        server_url: str,
        credentials: Optional[CredentialConfig] = None,
        additional_headers: Optional[
            Dict[str, Union[str, Callable[[], str], Callable[[], Awaitable[str]]]]
        ] = None,
        **kwargs: Any,
    ):
        """
        Args:
            server_url: The URL of the Toolbox server.
            credentials: The CredentialConfig object (from CredentialStrategy).
            additional_headers: Dictionary of headers (static or dynamic callables).
            **kwargs: Additional arguments passed to toolbox_core.ToolboxClient.
        """
        self._core_client_headers: Dict[
            str, Union[str, Callable[[], str], Callable[[], Awaitable[str]]]
        ] = {}
        self._credentials = credentials

        # Add static additional headers
        if additional_headers:
            for k, v in additional_headers.items():
                self._core_client_headers[k] = v

        if credentials:
            self._configure_auth(credentials)

        self._client = toolbox_core.ToolboxClient(
            url=server_url, client_headers=self._core_client_headers, **kwargs
        )

    def _configure_auth(self, creds: CredentialConfig) -> None:
        if creds.type == CredentialType.TOOLBOX_IDENTITY:
            # No auth headers needed
            pass

        elif creds.type == CredentialType.WORKLOAD_IDENTITY:
            if not creds.target_audience:
                raise ValueError(
                    "target_audience is required for WORKLOAD_IDENTITY"
                )

            # Create an async capable token getter
            self._core_client_headers["Authorization"] = self._create_adc_token_getter(
                creds.target_audience
            )

        elif creds.type == CredentialType.MANUAL_TOKEN:
            if not creds.token:
                raise ValueError("token is required for MANUAL_TOKEN")
            scheme = creds.scheme or "Bearer"
            self._core_client_headers["Authorization"] = f"{scheme} {creds.token}"

        elif creds.type == CredentialType.MANUAL_CREDS:
            if not creds.credentials:
                raise ValueError("credentials object is required for MANUAL_CREDS")

            # Adapter for google-auth credentials object to callable
            self._core_client_headers["Authorization"] = (
                self._create_creds_token_getter(creds.credentials)
            )

        elif creds.type == CredentialType.USER_IDENTITY:
            # For USER_IDENTITY (3LO), the *Tool* handles the interactive flow at runtime.

            def get_user_token() -> str:
                token = USER_TOKEN_CONTEXT_VAR.get()
                if not token:
                    return ""
                return f"Bearer {token}"

            header_name = getattr(creds, "header_name", "Authorization") or "Authorization"
            self._core_client_headers[header_name] = get_user_token

        elif creds.type == CredentialType.API_KEY:
            if not creds.api_key or not creds.header_name:
                raise ValueError("api_key and header_name are required for API_KEY")
            
            self._core_client_headers[creds.header_name] = creds.api_key

    def _create_adc_token_getter(self, audience: str) -> Callable[[], str]:
        """Returns a callable that fetches a fresh ID token using ADC."""

        def get_token() -> str:
            request = requests.Request()
            try:
                # Try fetching ID token directly (e.g. on Cloud Run/GKE with metadata server)
                token = id_token.fetch_id_token(request, audience)
                return f"Bearer {token}"
            except Exception:
                # Fallback to default credentials (e.g. local gcloud auth)
                creds, _ = google.auth.default()
                if not creds.valid:
                    creds.refresh(request)

                if hasattr(creds, "id_token") and creds.id_token:
                    return f"Bearer {creds.id_token}"

                curr_token = getattr(creds, "token", None)
                return f"Bearer {curr_token}" if curr_token else ""

        return get_token

    def _create_creds_token_getter(self, credentials: Any) -> Callable[[], str]:
        def get_token() -> str:
            request = requests.Request()
            if not credentials.valid:
                credentials.refresh(request)
            return f"Bearer {credentials.token}"

        return get_token

    @property
    def credential_config(self) -> Optional[CredentialConfig]:
        return self._credentials

    async def load_toolset(self, toolset_name: str, **kwargs: Any) -> Any:
        return await self._client.load_toolset(toolset_name, **kwargs)

    async def load_tool(self, tool_name: str, **kwargs: Any) -> Any:
        return await self._client.load_tool(tool_name, **kwargs)

    async def close(self):
        await self._client.close()
