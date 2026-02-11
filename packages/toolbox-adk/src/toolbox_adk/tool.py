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

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

import google.adk.auth.exchanger.oauth2_credential_exchanger as oauth2_credential_exchanger
import google.adk.auth.oauth2_credential_util as oauth2_credential_util
import toolbox_core
from fastapi.openapi.models import (
    OAuth2,
    OAuthFlowAuthorizationCode,
    OAuthFlows,
)
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.auth.auth_tool import AuthConfig
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai.types import FunctionDeclaration, Schema, Type
from toolbox_core.tool import ToolboxTool as CoreToolboxTool
from typing_extensions import override

from .client import USER_TOKEN_CONTEXT_VAR
from .credentials import CredentialConfig, CredentialType

# --- Monkey Patch ADK OAuth2 Exchange to Retain ID Tokens ---
# Google's ID Token is required by MCP Toolbox but ADK's `update_credential_with_tokens` natively drops the `id_token`.
# TODO(id_token): Remove this monkey patch once the PR https://github.com/google/adk-python/pull/4402 is merged.
_orig_update_cred = oauth2_credential_util.update_credential_with_tokens


def _patched_update_credential_with_tokens(auth_credential, tokens):
    _orig_update_cred(auth_credential, tokens)
    if tokens and "id_token" in tokens and auth_credential and auth_credential.oauth2:
        setattr(auth_credential.oauth2, "id_token", tokens["id_token"])


oauth2_credential_util.update_credential_with_tokens = (
    _patched_update_credential_with_tokens
)
oauth2_credential_exchanger.update_credential_with_tokens = (
    _patched_update_credential_with_tokens
)
# -------------------------------------------------------------


class ToolboxTool(BaseTool):
    """
    A tool that delegates to a remote Toolbox tool, integrated with ADK.
    """

    def __init__(
        self,
        core_tool: CoreToolboxTool,
        auth_config: Optional[CredentialConfig] = None,
    ):
        """
        Args:
            core_tool: The underlying toolbox_core.py tool instance.
            auth_config: Credential configuration to handle interactive flows.
        """
        # We act as a proxy.
        # We need to extract metadata from the core tool to satisfy BaseTool's contract.

        name = getattr(core_tool, "__name__", None)
        if not name:
            raise ValueError(f"Core tool {core_tool} must have a valid __name__")

        description = getattr(core_tool, "__doc__", None)
        if not description:
            raise ValueError(
                f"Core tool {name} must have a valid __doc__ (description)"
            )

        super().__init__(
            name=name,
            description=description,
            # Pass empty custom_metadata as it is not currently used
            custom_metadata={},
        )
        self._core_tool = core_tool
        self._auth_config = auth_config

    def _param_type_to_schema_type(self, param_type: str) -> Type:
        type_map = {
            "string": Type.STRING,
            "integer": Type.INTEGER,
            "number": Type.NUMBER,
            "boolean": Type.BOOLEAN,
            "array": Type.ARRAY,
            "object": Type.OBJECT,
        }
        return type_map.get(param_type, Type.STRING)

    @override
    def _get_declaration(self) -> Optional[FunctionDeclaration]:
        """Gets the function declaration for the tool."""
        properties = {}
        required = []

        # We do not use `google.genai.types.FunctionDeclaration.from_callable`
        # here because it explicitly drops argument descriptions from the schema
        # properties, lumping them all into the root description instead.
        if hasattr(self._core_tool, "_params") and self._core_tool._params:
            for param in self._core_tool._params:
                properties[param.name] = Schema(
                    type=self._param_type_to_schema_type(param.type),
                    description=param.description or "",
                )
                if param.required:
                    required.append(param.name)

        parameters = (
            Schema(type=Type.OBJECT, properties=properties, required=required)
            if properties
            else None
        )

        return FunctionDeclaration(
            name=self.name, description=self.description, parameters=parameters
        )

    @override
    async def run_async(
        self,
        args: Dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        # Check if USER_IDENTITY is configured
        reset_token = None

        if self._auth_config and self._auth_config.type == CredentialType.USER_IDENTITY:
            requires_auth = (
                len(self._core_tool._required_authn_params) > 0
                or len(self._core_tool._required_authz_tokens) > 0
            )

            if requires_auth:
                if (
                    not self._auth_config.client_id
                    or not self._auth_config.client_secret
                ):
                    raise ValueError(
                        "USER_IDENTITY requires client_id and client_secret"
                    )

                # Construct ADK AuthConfig
                scopes = self._auth_config.scopes or ["openid", "profile", "email"]
                scope_dict = {s: "" for s in scopes}

                auth_config_adk = AuthConfig(
                    auth_scheme=OAuth2(
                        flows=OAuthFlows(
                            authorizationCode=OAuthFlowAuthorizationCode(
                                authorizationUrl="https://accounts.google.com/o/oauth2/auth",
                                tokenUrl="https://oauth2.googleapis.com/token",
                                scopes=scope_dict,
                            )
                        )
                    ),
                    raw_auth_credential=AuthCredential(
                        auth_type=AuthCredentialTypes.OAUTH2,
                        oauth2=OAuth2Auth(
                            client_id=self._auth_config.client_id,
                            client_secret=self._auth_config.client_secret,
                        ),
                    ),
                )

                # Check if we already have credentials from a previous exchange
                try:
                    # Try to load credential from credential service first (persists across sessions)
                    creds = None
                    try:
                        if tool_context._invocation_context.credential_service:
                            creds = await tool_context._invocation_context.credential_service.load_credential(
                                auth_config=auth_config_adk,
                                callback_context=tool_context,
                            )
                    except ValueError:
                        # Credential service might not be initialized
                        pass

                    if not creds:
                        # Fallback to session state (get_auth_response returns AuthCredential if found)
                        creds = tool_context.get_auth_response(auth_config_adk)

                    if creds and creds.oauth2 and creds.oauth2.access_token:
                        reset_token = USER_TOKEN_CONTEXT_VAR.set(
                            creds.oauth2.access_token
                        )

                        # Bind the token to the underlying core_tool so it constructs headers properly
                        needed_services = set()
                        for requested_service in list(
                            self._core_tool._required_authn_params.values()
                        ) + list(self._core_tool._required_authz_tokens):
                            if isinstance(requested_service, list):
                                needed_services.update(requested_service)
                            else:
                                needed_services.add(requested_service)

                        for s in needed_services:
                            # Only add if not already registered (prevents ValueError on duplicate params or subsequent runs)
                            if (
                                not hasattr(self._core_tool, "_auth_token_getters")
                                or s not in self._core_tool._auth_token_getters
                            ):
                                # TODO(id_token): Uncomment this line and remove the `getattr` fallback below once PR https://github.com/google/adk-python/pull/4402 is merged.
                                # self._core_tool = self._core_tool.add_auth_token_getter(s, lambda t=creds.oauth2.id_token or creds.oauth2.access_token: t)
                                self._core_tool = self._core_tool.add_auth_token_getter(
                                    s,
                                    lambda t=getattr(
                                        creds.oauth2,
                                        "id_token",
                                        creds.oauth2.access_token,
                                    ): t,
                                )
                        # Once we use it from get_auth_response, save it to the auth service for future use
                        try:
                            if tool_context._invocation_context.credential_service:
                                auth_config_adk.exchanged_auth_credential = creds
                                await tool_context._invocation_context.credential_service.save_credential(
                                    auth_config=auth_config_adk,
                                    callback_context=tool_context,
                                )
                        except Exception as e:
                            logging.debug(f"Failed to save credential to service: {e}")
                    else:
                        tool_context.request_credential(auth_config_adk)
                        return {
                            "error": f"OAuth2 Credentials required for {self.name}. A consent link has been generated for the user. Do NOT attempt to run this tool again until the user confirms they have logged in."
                        }
                except Exception as e:
                    if "credential" in str(e).lower() or isinstance(e, ValueError):
                        raise e

                    logging.warning(
                        f"Unexpected error in get_auth_response during User Identity (OAuth2) retrieval: {e}. "
                        "Falling back to request_credential.",
                        exc_info=True,
                    )
                    # Fallback to request logic
                    tool_context.request_credential(auth_config_adk)
                    return {
                        "error": f"OAuth2 Credentials required for {self.name}. A consent link has been generated for the user. Do NOT attempt to run this tool again until the user confirms they have logged in."
                    }

        result: Optional[Any] = None
        error: Optional[Exception] = None

        try:
            # Execute the core tool
            result = await self._core_tool(**args)
            return result

        except Exception as e:
            error = e
            raise e
        finally:
            if reset_token:
                USER_TOKEN_CONTEXT_VAR.reset(reset_token)

    def bind_params(self, bounded_params: Dict[str, Any]) -> "ToolboxTool":
        """Allows runtime binding of parameters, delegating to core tool."""
        new_core_tool = self._core_tool.bind_params(bounded_params)
        # Return a new wrapper
        return ToolboxTool(
            core_tool=new_core_tool,
            auth_config=self._auth_config,
        )
