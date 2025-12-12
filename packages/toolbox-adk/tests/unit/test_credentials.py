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

from toolbox_adk.credentials import CredentialStrategy, CredentialType


class TestCredentialStrategy:
    def test_toolbox_identity(self):
        config = CredentialStrategy.toolbox_identity()
        assert config.type == CredentialType.TOOLBOX_IDENTITY

    def test_workload_identity(self):
        audience = "https://example.com"
        config = CredentialStrategy.workload_identity(audience)
        assert config.type == CredentialType.WORKLOAD_IDENTITY
        assert config.target_audience == audience

    def test_application_default_credentials_alias(self):
        audience = "https://example.com"
        config = CredentialStrategy.application_default_credentials(audience)
        assert config.type == CredentialType.WORKLOAD_IDENTITY
        assert config.target_audience == audience

    def test_user_identity(self):
        config = CredentialStrategy.user_identity(
            client_id="id", client_secret="secret", scopes=["scope1"]
        )
        assert config.type == CredentialType.USER_IDENTITY
        assert config.client_id == "id"
        assert config.client_secret == "secret"
        assert config.scopes == ["scope1"]

    def test_manual_token(self):
        config = CredentialStrategy.manual_token(token="abc", scheme="Custom")
        assert config.type == CredentialType.MANUAL_TOKEN
        assert config.token == "abc"
        assert config.scheme == "Custom"

    def test_manual_token_defaults(self):
        config = CredentialStrategy.manual_token(token="abc")
        assert config.scheme == "Bearer"

    def test_manual_creds(self):
        fake_creds = object()
        config = CredentialStrategy.manual_creds(fake_creds)
        assert config.type == CredentialType.MANUAL_CREDS
        assert config.credentials == fake_creds

    def test_from_adk_credentials_oauth2(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
            OAuth2Auth,
        )
        from fastapi.openapi.models import OAuth2, OAuthFlows
            
        # Mock objects
        oauth2_auth = OAuth2Auth(
            client_id="cid", client_secret="csec", scopes=["s1"]
        )
        cred = AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2, oauth2=oauth2_auth
        )
        # Scheme is required for type hinting but not used for OAuth2 in this impl
        scheme = OAuth2(flows=OAuthFlows())
        
        config = CredentialStrategy.from_adk_credentials(scheme, cred)
        assert config.type == CredentialType.USER_IDENTITY
        assert config.client_id == "cid"
        assert config.client_secret == "csec"
        assert config.scopes == ["s1"]

    def test_from_adk_credentials_http_bearer(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
            HttpCredentials,
            HttpAuth,
        )
        from fastapi.openapi.models import HTTPBearer
            
        http_creds = HttpCredentials(token="xyz")
        http_auth = HttpAuth(scheme="Bearer", credentials=http_creds)
        cred = AuthCredential(
            auth_type=AuthCredentialTypes.HTTP, http=http_auth
        )
        scheme = HTTPBearer()

        config = CredentialStrategy.from_adk_credentials(scheme, cred)
        assert config.type == CredentialType.MANUAL_TOKEN
        assert config.token == "xyz"
        assert config.scheme == "Bearer"

    def test_from_adk_auth_config(self):
        from google.adk.auth.auth_tool import AuthConfig
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
            OAuth2Auth,
        )
        from fastapi.openapi.models import OAuth2, OAuthFlows

        oauth2_auth = OAuth2Auth(
            client_id="cid2", client_secret="csec2", scopes=["s2"]
        )
        cred = AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2, oauth2=oauth2_auth
        )
        scheme = OAuth2(flows=OAuthFlows())
        auth_config = AuthConfig(auth_scheme=scheme, raw_auth_credential=cred)

        config = CredentialStrategy.from_adk_auth_config(auth_config)
        assert config.type == CredentialType.USER_IDENTITY
        assert config.client_id == "cid2"

