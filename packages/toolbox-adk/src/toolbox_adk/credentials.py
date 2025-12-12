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

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from google.auth import credentials as google_creds
from google.adk.auth.auth_credential import AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_tool import AuthConfig, AuthScheme


class CredentialType(Enum):
    TOOLBOX_IDENTITY = "TOOLBOX_IDENTITY"
    WORKLOAD_IDENTITY = "WORKLOAD_IDENTITY"
    USER_IDENTITY = "USER_IDENTITY"
    MANUAL_TOKEN = "MANUAL_TOKEN"
    MANUAL_CREDS = "MANUAL_CREDS"
    API_KEY = "API_KEY"


@dataclass
class CredentialConfig:
    type: CredentialType
    # For WORKLOAD_IDENTITY
    target_audience: Optional[str] = None
    # For USER_IDENTITY
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scopes: Optional[List[str]] = None
    # For MANUAL_TOKEN
    token: Optional[str] = None
    scheme: Optional[str] = None
    # For MANUAL_CREDS
    credentials: Optional[google_creds.Credentials] = None
    # For API_KEY
    api_key: Optional[str] = None
    # Common
    header_name: Optional[str] = None


class CredentialStrategy:
    """Factory for creating credential configurations for ToolboxToolset."""

    @staticmethod
    def toolbox_identity() -> CredentialConfig:
        """
        No credentials are sent. Relies on the remote Toolbox server's own identity.
        """
        return CredentialConfig(type=CredentialType.TOOLBOX_IDENTITY)

    @staticmethod
    def workload_identity(target_audience: str) -> CredentialConfig:
        """
        Uses the agent ADC to generate a Google-signed ID token for the specified audience.
        This is suitable for Cloud Run, GKE, or local development with `gcloud auth login`.
        """
        return CredentialConfig(
            type=CredentialType.WORKLOAD_IDENTITY,
            target_audience=target_audience,
        )

    @staticmethod
    def application_default_credentials(target_audience: str) -> CredentialConfig:
        """
        Alias for workload_identity.
        """
        return CredentialStrategy.workload_identity(target_audience)

    @staticmethod
    def user_identity(
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        header_name: Optional[str] = None,
    ) -> CredentialConfig:
        """
        Configures the ADK-native interactive 3-legged OAuth flow to get consent
        and credentials from the end-user at runtime.
        """
        return CredentialConfig(
            type=CredentialType.USER_IDENTITY,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            header_name=header_name,
        )

    @staticmethod
    def manual_token(token: str, scheme: str = "Bearer") -> CredentialConfig:
        """
        Send a hardcoded token string in the Authorization header.
        """
        return CredentialConfig(
            type=CredentialType.MANUAL_TOKEN,
            token=token,
            scheme=scheme,
        )

    @staticmethod
    def manual_credentials(credentials: google_creds.Credentials) -> CredentialConfig:
        """
        Uses a provided Google Auth Credentials object.
        """
        return CredentialConfig(
            type=CredentialType.MANUAL_CREDS,
            credentials=credentials,
        )

    @staticmethod
    def api_key(key: str, header_name: str = "X-API-Key") -> CredentialConfig:
        """
        Configures an API Key to be sent in a specific header.
        """
        return CredentialConfig(
            type=CredentialType.API_KEY,
            api_key=key,
            header_name=header_name,
        )

    @staticmethod
    def from_adk_auth_config(auth_config: AuthConfig) -> CredentialConfig:
        """
        Creates a CredentialConfig from an ADK AuthConfig object.

        Args:
            auth_config: The ADK AuthConfig object.

        Returns:
            CredentialConfig: The corresponding credential configuration.
        """
        if auth_config.raw_auth_credential is None:
            raise ValueError("AuthConfig must have a raw_auth_credential.")

        return CredentialStrategy.from_adk_credentials(
            auth_credential=auth_config.raw_auth_credential,
            auth_scheme=auth_config.auth_scheme,
        )

    @staticmethod
    def from_adk_credentials(
        auth_credential: AuthCredential, auth_scheme: Optional[AuthScheme] = None
    ) -> CredentialConfig:
        """
        Creates a CredentialConfig from ADK AuthScheme and AuthCredential objects.

        Args:
            auth_credential: The ADK AuthCredential (containing secrets/tokens).
            auth_scheme: The ADK AuthScheme (e.g. OAuth2, HTTP, API Key etc).
                         Required for API Key credentials. Optional for others.

        Returns:
            CredentialConfig: The corresponding credential configuration.

        Raises:
            ValueError: If the credential type is not supported or required scheme is missing.
        """
        # Handle OAuth2
        if (
            auth_credential.auth_type == AuthCredentialTypes.OAUTH2
            and auth_credential.oauth2
        ):
            # Extract client_id, client_secret, and scopes from the credential object.
            return CredentialStrategy.user_identity(
                client_id=auth_credential.oauth2.client_id,
                client_secret=auth_credential.oauth2.client_secret,
                scopes=auth_credential.oauth2.scopes,
            )

        # Handle HTTP Bearer
        if (
            auth_credential.auth_type == AuthCredentialTypes.HTTP
            and auth_credential.http
        ):
            scheme_type = (auth_credential.http.scheme or "").lower()
            if (
                scheme_type == "bearer"
                and auth_credential.http.credentials
                and auth_credential.http.credentials.token
            ):
                return CredentialStrategy.manual_token(
                    token=auth_credential.http.credentials.token, scheme="Bearer"
                )
            
            raise ValueError(
                f"Unsupported HTTP authentication scheme: {scheme_type}"
            )

        if (
            auth_credential.auth_type == AuthCredentialTypes.API_KEY
            and auth_credential.api_key
        ):
            if not auth_scheme:
                raise ValueError("API Key credentials require the auth_scheme definition.")
            
            header_name = getattr(auth_scheme, "name", None)
            if not header_name:
                raise ValueError("API Key scheme must define the header name.")
            
            location = getattr(auth_scheme, "in_", "header") or "header"
            # Handle Enum (APIKeyIn.header) or string values
            location_str = str(location)
            if "." in location_str:
                location_str = location_str.split(".")[-1]
            
            if location_str.lower() != "header":
                raise ValueError(
                    f"Unsupported API Key location: {location}. Only 'header' is supported."
                )

            return CredentialStrategy.api_key(
                key=auth_credential.api_key,
                header_name=header_name,
            )

        raise ValueError(
            f"Unsupported ADK credential type: {auth_credential.auth_type}"
        )
