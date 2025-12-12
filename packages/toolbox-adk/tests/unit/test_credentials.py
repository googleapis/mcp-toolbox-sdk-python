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

    def test_manual_credentials(self):
        fake_creds = object()
        config = CredentialStrategy.manual_credentials(fake_creds)
        assert config.type == CredentialType.MANUAL_CREDS
        assert config.credentials == fake_creds

    def test_api_key(self):
        config = CredentialStrategy.api_key(key="123", header_name="x-custom")
        assert config.type == CredentialType.API_KEY
        assert config.api_key == "123"
        assert config.header_name == "x-custom"

    def test_from_adk_credentials_oauth2(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
            OAuth2Auth,
        )
        from fastapi.openapi.models import OAuth2, OAuthFlows

        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2,
            oauth2=OAuth2Auth(
                client_id="cid", client_secret="csec", scopes=["scope"]
            ),
        )
        # Call without auth_scheme
        config = CredentialStrategy.from_adk_credentials(
            auth_credential=auth_credential
        )
        assert config.type == CredentialType.USER_IDENTITY
        assert config.client_id == "cid"
        assert config.client_secret == "csec"
        assert config.scopes == ["scope"]

    def test_from_adk_credentials_http_bearer(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
            HttpAuth,
            HttpCredentials,
        )
        from fastapi.openapi.models import HTTPBearer

        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.HTTP,
            http=HttpAuth(
                scheme="Bearer", credentials=HttpCredentials(token="my-token")
            ),
        )
        # Call without auth_scheme
        config = CredentialStrategy.from_adk_credentials(
            auth_credential=auth_credential
        )
        assert config.type == CredentialType.MANUAL_TOKEN
        assert config.token == "my-token"
        assert config.scheme == "Bearer"

    def test_from_adk_credentials_api_key(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
        )
        from fastapi.openapi.models import APIKey, APIKeyIn
        
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.API_KEY, api_key="abc"
        )
        # Pass 'in' directly via dict unpacking to avoid alias issues
        auth_scheme = APIKey(type="apiKey", name="x-api-key", **{"in": APIKeyIn.header})
        
        config = CredentialStrategy.from_adk_credentials(
            auth_credential=auth_credential, auth_scheme=auth_scheme
        )
        assert config.type == CredentialType.API_KEY
        assert config.api_key == "abc"
        assert config.header_name == "x-api-key"

    def test_from_adk_credentials_api_key_default_location(self):
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
        )
        from fastapi.openapi.models import APIKey
        
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.API_KEY, api_key="abc"
        )
        # Omit 'in' / 'in_'
        # We simulate an object that lacks 'in_' or has it as None
        # Using a simple namespace or partial mock since APIKey might enforce required fields if verified strictly
        # But let's assume usage where it might be missing or we use a loose object.
        # Actually fastapi APIKey requires 'in_', so we might need to mock or use a cleaner dict approach if supporting loose objects.
        # ADK AuthScheme is typically a Pydantic model.
        # Let's try to construct APIKey without 'in' if possible, or use a mock.
        auth_scheme = APIKey(type="apiKey", name="x-api-key", **{"in": "header"}) # This is explicit.
        # To test DEFAULT, we need an object that returns None for .in_
        
        class MockScheme:
            name = "x-api-key"
            in_ = None
            
        config = CredentialStrategy.from_adk_credentials(
            auth_credential=auth_credential, auth_scheme=MockScheme()
        )
        assert config.type == CredentialType.API_KEY
        assert config.api_key == "abc"
        assert config.header_name == "x-api-key"

    def test_from_adk_credentials_api_key_query_fail(self):
        import pytest
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
        )
        from fastapi.openapi.models import APIKey, APIKeyIn
    
        cred = AuthCredential(auth_type=AuthCredentialTypes.API_KEY, api_key="abc")
        scheme = APIKey(type="apiKey", name="key", **{"in": APIKeyIn.query})
    
        with pytest.raises(ValueError, match="Unsupported API Key location"):
            CredentialStrategy.from_adk_credentials(auth_credential=cred, auth_scheme=scheme)

    def test_from_adk_credentials_api_key_no_scheme_raises(self):
        import pytest
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
        )
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.API_KEY, api_key="my-key"
        )
        with pytest.raises(ValueError, match="API Key credentials require the auth_scheme definition"):
            CredentialStrategy.from_adk_credentials(auth_credential=auth_credential)

    def test_from_adk_credentials_unsupported(self):
        import pytest
        from google.adk.auth.auth_credential import (
            AuthCredential,
            AuthCredentialTypes,
        )
        auth_credential = AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2
        )  # No oauth2 data
        with pytest.raises(ValueError, match="Unsupported ADK credential type"):
            # Scheme is optional now, so we can omit it here too
            CredentialStrategy.from_adk_credentials(auth_credential=auth_credential)

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
