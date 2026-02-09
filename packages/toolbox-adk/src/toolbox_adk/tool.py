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
from google.genai.types import FunctionDeclaration, Type, Schema
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
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
        pre_hook: Optional[Callable[[ToolContext, Dict[str, Any]], Awaitable[None]]] = None,
        post_hook: Optional[
            Callable[[ToolContext, Dict[str, Any], Optional[Any], Optional[Exception]], Awaitable[None]]
        ] = None,
        auth_config: Optional[CredentialConfig] = None,
    ):
        """
        Args:
            core_tool: The underlying toolbox_core.py tool instance.
            pre_hook: Async function called before execution. Receives (tool_context, arguments).
            post_hook: Async function called after execution. Receives (tool_context, arguments, result, error).
            auth_config: Credential configuration to handle interactive flows.
        """
        # We act as a proxy.
        # We need to extract metadata from the core tool to satisfy BaseTool's contract.

        name = getattr(core_tool, "__name__", None)
        if not name:
            raise ValueError(f"Core tool {core_tool} must have a valid __name__")

        description = getattr(core_tool, "__doc__", None)
        if not description:
            raise ValueError(f"Core tool {name} must have a valid __doc__ (description)")

        super().__init__(
            name=name,
            description=description,
            # Pass empty custom_metadata as it is not currently used
            custom_metadata={},
        )
        self._core_tool = core_tool
        self._pre_hook = pre_hook
        self._post_hook = post_hook
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
        
        # We do not use `google.genai.types.FunctionDeclaration.from_callable` here
        # because it explicitly drops argument descriptions from the schema properties,
        # lumping them all into the root description instead.
        if hasattr(self._core_tool, '_params') and self._core_tool._params:
            for param in self._core_tool._params:
                properties[param.name] = Schema(
                    type=self._param_type_to_schema_type(param.type),
                    description=param.description or ""
                )
                if param.required:
                    required.append(param.name)

        parameters = Schema(
            type=Type.OBJECT,
            properties=properties,
            required=required
        ) if properties else None

        return FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=parameters
        )

    @override
    async def run_async(
        self,
        args: Dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        if self._pre_hook:
            await self._pre_hook(tool_context, args)

        # Check if USER_IDENTITY is configured
        reset_token = None

        if self._auth_config and self._auth_config.type == CredentialType.USER_IDENTITY:
            if not self._auth_config.client_id or not self._auth_config.client_secret:
                raise ValueError("USER_IDENTITY requires client_id and client_secret")

            # Construct ADK AuthConfig
            scopes = self._auth_config.scopes or [
                "https://www.googleapis.com/auth/cloud-platform"
            ]
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
                # get_auth_response returns AuthCredential if found
                creds = tool_context.get_auth_response(auth_config_adk)
                if creds and creds.oauth2 and creds.oauth2.access_token:
                    reset_token = USER_TOKEN_CONTEXT_VAR.set(creds.oauth2.access_token)
                else:
                    # Request credentials and pause execution
                    tool_context.request_credential(auth_config_adk)
                    return None
            except Exception as e:
                if "credential" in str(e).lower() or isinstance(e, ValueError):
                    raise e
                
                logging.warning(
                    f"Unexpected error in get_auth_response during User Identity (OAuth2) retrieval: {e}. "
                    "Falling back to request_credential.",
                    exc_info=True
                )
                # Fallback to request logic
                tool_context.request_credential(auth_config_adk)
                return None

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
            if self._post_hook:
                await self._post_hook(tool_context, args, result, error)

    def bind_params(self, bounded_params: Dict[str, Any]) -> "ToolboxTool":
        """Allows runtime binding of parameters, delegating to core tool."""
        new_core_tool = self._core_tool.bind_params(bounded_params)
        # Return a new wrapper
        return ToolboxTool(
            core_tool=new_core_tool,
            pre_hook=self._pre_hook,
            post_hook=self._post_hook,
            auth_config=self._auth_config,
        )
