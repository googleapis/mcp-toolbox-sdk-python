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
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

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
from toolbox_core.protocol import (
    AdditionalPropertiesSchema,
    ParameterSchema,
    TelemetryAttributes,
)
from toolbox_core.tool import ToolboxTool as CoreToolboxTool
from typing_extensions import override

from .client import USER_TOKEN_CONTEXT_VAR
from .credentials import CredentialConfig, CredentialType


class ToolboxTool(BaseTool):
    """
    A tool that delegates to a remote Toolbox tool, integrated with ADK.
    """

    def __init__(
        self,
        core_tool: CoreToolboxTool,
        auth_config: Optional[CredentialConfig] = None,
        adk_token_getters: Optional[Mapping[str, Any]] = None,
        telemetry_attributes: Optional[TelemetryAttributes] = None,
    ):
        """
        Args:
            core_tool: The underlying toolbox_core.py tool instance.
            auth_config: Credential configuration to handle interactive flows.
            adk_token_getters: Tool-specific auth token getters.
            telemetry_attributes: Optional telemetry attributes (agent_id, user_id, model) injected into each tool invocation.
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
        self._adk_token_getters = adk_token_getters or {}
        self._telemetry_attributes = telemetry_attributes

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
        schema_additional_properties = None

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

        # We do not use `google.genai.types.FunctionDeclaration.from_callable`
        # here because it explicitly drops argument descriptions from the schema
        # properties, lumping them all into the root description instead.
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
                                self._core_tool = self._core_tool.add_auth_token_getter(
                                    s,
                                    lambda t=creds.oauth2.id_token or creds.oauth2.access_token: t,
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
                    tool_context.request_credential(auth_config_adk)
                    return {
                        "error": f"OAuth2 Credentials required for {self.name}. A consent link has been generated for the user. Do NOT attempt to run this tool again until the user confirms they have logged in."
                    }

        if self._adk_token_getters:
            # Pre-filter toolset getters to avoid unused-token errors from the core tool.
            # This deferred loop also enables dynamic 1-arity `tool_context` injection.
            needed_services = set()
            for reqs in self._core_tool._required_authn_params.values():
                needed_services.update(reqs)
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

        result: Optional[Any] = None
        error: Optional[Exception] = None

        try:
            # Execute the core tool, injecting telemetry_attributes if configured
            if self._telemetry_attributes:
                args["telemetry_attributes"] = self._telemetry_attributes
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
            adk_token_getters=self._adk_token_getters,
            telemetry_attributes=self._telemetry_attributes,
        )
