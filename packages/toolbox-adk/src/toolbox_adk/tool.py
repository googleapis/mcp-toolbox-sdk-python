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

import inspect
import logging
from typing import Any, Dict, Mapping, Optional
from pydantic import ValidationError

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
from toolbox_core.protocol import AdditionalPropertiesSchema, ParameterSchema
from toolbox_core.tool import ToolboxTool as CoreToolboxTool
from typing_extensions import override

from .client import USER_TOKEN_CONTEXT_VAR
from .credentials import CredentialConfig, CredentialType


class ToolboxTool(BaseTool):
    """A tool that delegates to a remote Toolbox tool, integrated with ADK."""

    def __init__(
        self,
        core_tool: CoreToolboxTool,
        auth_config: Optional[CredentialConfig] = None,
        adk_token_getters: Optional[Mapping[str, Any]] = None,
    ):
        """Args:
            core_tool: The underlying toolbox_core.py tool instance.
            auth_config: Credential configuration to handle interactive flows.
            adk_token_getters: Tool-specific auth token getters.
        """
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
            custom_metadata={},
        )
        self._core_tool = core_tool
        self._auth_config = auth_config
        self._adk_token_getters = adk_token_getters or {}

    def _param_type_to_schema_type(self, param_type: str) -> Type:
        type_map = {
            "string": Type.STRING,
            "integer": Type.INTEGER,
            "float": Type.NUMBER,
            "number": Type.NUMBER,
            "boolean": Type.BOOLEAN,
            "array": Type.ARRAY,
            "object": Type.OBJECT,
        }
        return type_map.get(param_type, Type.STRING)

    def _build_schema(self, param: Any) -> Schema:
        """Builds a Schema from a parameter."""
        param_type = getattr(param, "type", "string")
        schema_type = self._param_type_to_schema_type(param_type)
        properties = {}
        required = []
        schema_items = None

        if schema_type == Type.ARRAY:
            if hasattr(param, "items") and param.items:
                schema_items = self._build_schema(param.items)
        elif schema_type == Type.OBJECT:
            nested_properties = getattr(param, "properties", None)
            if nested_properties:
                for k, v in nested_properties.items():
                    properties[k] = self._build_schema(v)
                    if getattr(v, "required", False):
                        required.append(k)

        return Schema(
            type=schema_type,
            description=getattr(param, "description", "") or "",
            properties=properties or None,
            required=required or None,
            items=schema_items,
        )

    @override
    def _get_declaration(self) -> Optional[FunctionDeclaration]:
        """Gets the function declaration for the tool."""
        properties = {}
        required = []
        if hasattr(self._core_tool, "_params") and self._core_tool._params:
            for param in self._core_tool._params:
                properties[param.name] = self._build_schema(param)
                if param.required:
                    required.append(param.name)

        parameters = (
            Schema(
                type=Type.OBJECT,
                properties=properties,
                required=required or None,
            )
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

                try:
                    creds = None
                    try:
                        if tool_context._invocation_context.credential_service:
                            creds = await tool_context._invocation_context.credential_service.load_credential(
                                auth_config=auth_config_adk,
                                callback_context=tool_context,
                            )
                    except ValueError:
                        pass

                    if not creds:
                        creds = tool_context.get_auth_response(auth_config_adk)

                    if creds and creds.oauth2 and creds.oauth2.access_token:
                        reset_token = USER_TOKEN_CONTEXT_VAR.set(
                            creds.oauth2.access_token
                        )

                        needed_services = set()
                        for requested_service in list(
                            self._core_tool._required_authn_params.values()
                        ) + list(self._core_tool._required_authz_tokens):
                            if isinstance(requested_service, list):
                                needed_services.update(requested_service)
                            else:
                                needed_services.add(requested_service)

                        for s in needed_services:
                            if (
                                not hasattr(self._core_tool, "_auth_token_getters")
                                or s not in self._core_tool._auth_token_getters
                            ):
                                self._core_tool = self._core_tool.add_auth_token_getter(
                                    s,
                                    lambda t=creds.oauth2.id_token
                                    or creds.oauth2.access_token: t,
                                )
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
                    tool_context.request_credential(auth_config_adk)
                    return {
                        "error": f"OAuth2 Credentials required for {self.name}. A consent link has been generated for the user. Do NOT attempt to run this tool again until the user confirms they have logged in."
                    }

        if self._adk_token_getters:
            # Pre-filter toolset getters to avoid unused-token errors from the core tool.
            # This deferred loop also enables dynamic 1-arity `tool_context` injection.
            needed_services = set()
            for reqs in self._core_tool._required_authn_params.values():
                if isinstance(reqs, list):
                    needed_services.update(reqs)
                else:
                    needed_services.add(reqs)
            needed_services.update(self._core_tool._required_authz_tokens)

            for service, getter in self._adk_token_getters.items():
                if service in needed_services:
                    sig = inspect.signature(getter)
                    if len(sig.parameters) == 1:
                        bound_getter = lambda t=getter, ctx=tool_context: t(ctx)
                    else:
                        bound_getter = getter
                    self._core_tool = self._core_tool.add_auth_token_getter(
                        service, bound_getter
                    )

        try:
            return await self._core_tool(**args)
        except (TypeError, PermissionError, ValueError, ValidationError) as e:
            # Propagate framework-level errors to ensure compatibility with existing tests
            raise e
        except Exception as e:
            # Catch unexpected tool execution errors and return as a structured dictionary
            # This handles cases like remote tool crashes or server errors gracefully for LLMs
            logging.warning(
                "Toolbox tool '%s' execution failed: %s", self.name, e, exc_info=True
            )
            return {"error": f"{type(e).__name__}: {e}", "is_error": True}
        finally:
            if reset_token:
                USER_TOKEN_CONTEXT_VAR.reset(reset_token)

    def bind_params(self, bounded_params: Dict[str, Any]) -> "ToolboxTool":
        new_core_tool = self._core_tool.bind_params(bounded_params)
        return ToolboxTool(
            core_tool=new_core_tool,
            auth_config=self._auth_config,
            adk_token_getters=self._adk_token_getters,
        )
