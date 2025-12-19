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

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from google.auth import credentials as google_creds


class CredentialType(Enum):
    TOOLBOX_IDENTITY = "TOOLBOX_IDENTITY"
    APPLICATION_DEFAULT_CREDENTIALS = "APPLICATION_DEFAULT_CREDENTIALS"
    USER_IDENTITY = "USER_IDENTITY"
    MANUAL_TOKEN = "MANUAL_TOKEN"
    MANUAL_CREDS = "MANUAL_CREDS"


@dataclass
class CredentialConfig:
    type: CredentialType
    # For APPLICATION_DEFAULT_CREDENTIALS
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
        client_id: str, client_secret: str, scopes: Optional[List[str]] = None
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
