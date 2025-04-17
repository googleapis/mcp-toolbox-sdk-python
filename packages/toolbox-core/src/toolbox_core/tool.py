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


import types
from copy import deepcopy
from inspect import Signature
from typing import Any, Callable, Mapping, Optional, Sequence, Union
from warnings import warn

from aiohttp import ClientSession
from pydantic import ValidationError

from toolbox_core.protocol import ParameterSchema

from .utils import (
    create_func_docstring,
    identify_required_authn_params,
    params_to_pydantic_model,
    resolve_value,
)


class ToolboxTool:
    """
    A callable proxy object representing a specific tool on a remote Toolbox server.

    Instances of this class behave like asynchronous functions. When called, they
    send a request to the corresponding tool's endpoint on the Toolbox server with
    the provided arguments.

    It utilizes Python's introspection features (`__name__`, `__doc__`,
    `__signature__`, `__annotations__`) so that standard tools like `help()`
    and `inspect` work as expected.
    """

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        name: str,
        description: str,
        params: Sequence[ParameterSchema],
        auth_service_token_getters: Mapping[str, Callable[[], str]],
        bound_params: Mapping[str, Union[Callable[[], Any], Any]],
        strict: bool = True,
        __original_params: Optional[Sequence[ParameterSchema]] = None,
        __original_required_authn_params: Optional[Mapping[str, list[str]]] = None,
    ):
        """
        Initializes a callable that will trigger the tool invocation through the
        Toolbox server.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            description: The description of the remote tool.
            params: The *complete* original parameter list for the tool.
            auth_service_token_getters: A dict of authService -> token (or callables that
                produce a token)
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            strict: If True (default), raises ValueError during initialization or
                    binding if parameters are missing, already bound, or require
                    authentication. If False, issues a warning for auth conflicts
                    instead (missing/duplicate bindings still raise errors).
        """
        self.__session: ClientSession = session
        self.__base_url: str = base_url
        self.__name__ = name
        self.__description = description
        self.__strict = strict

        self.__original_params = deepcopy(
            __original_params if __original_params is not None else params
        )
        self.__original_required_authn_params = (
            __original_required_authn_params
            if __original_required_authn_params is not None
            else identify_required_authn_params(self.__original_params)
        )

        # Validate initial bound_params against original schema before setting state
        self._validate_binding(bound_params, check_already_bound=False)

        # Initialize internal state based on current bindings
        self.__auth_service_token_getters = types.MappingProxyType(
            dict(auth_service_token_getters)
        )
        self.__bound_parameters = types.MappingProxyType(
            dict(bound_params)
        )

        # Filter original params to get current (unbound) params
        self.__params = tuple(
            p for p in self.__original_params if p.name not in self.__bound_parameters
        )

        # Setup for invocation and introspection based on *current* params
        self.__url = f"{self.__base_url}/api/tool/{self.__name__}/invoke"
        self.__pydantic_model = params_to_pydantic_model(self.__name__, self.__params)

        inspect_type_params = [
            param.to_param() for param in self.__params
        ]

        self.__doc__ = create_func_docstring(
            self.__description, self.__params
        )
        self.__signature__ = Signature(
            parameters=inspect_type_params, return_annotation=str
        )
        self.__annotations__ = {
            p.name: p.annotation for p in inspect_type_params
        }
        self.__qualname__ = f"{self.__class__.__qualname__}.{self.__name__}"


    def _validate_binding(
        self,
        params_to_validate: Mapping[str, Union[Callable[[], Any], Any]],
        check_already_bound: bool = True,
    ) -> None:
        """
        Validates parameters intended for binding against the original schema
        and authentication requirements, respecting the instance's strict mode.
        """
        auth_bound_params: list[str] = []
        missing_bound_params: list[str] = []
        already_bound_params: list[str] = []

        original_param_names = {p.name for p in self.__original_params}

        for param_name in params_to_validate:
            # Check if already bound (if requested)
            if check_already_bound and param_name in self.__bound_parameters:
                already_bound_params.append(param_name)
                continue

            # Check if missing from original schema
            if param_name not in original_param_names:
                missing_bound_params.append(param_name)
                continue

            # Check if requires authentication
            if param_name in self.__original_required_authn_params:
                auth_bound_params.append(param_name)

        if already_bound_params:
            raise ValueError(
                f"Parameter(s) `{', '.join(already_bound_params)}` already bound in tool `{self.__name__}`."
            )

        messages: list[str] = []
        if missing_bound_params:
            messages.append(
                f"Parameter(s) `{', '.join(missing_bound_params)}` not found in tool schema and cannot be bound."
            )
            raise ValueError("\n".join(messages))

        # Check auth conflicts separately
        if auth_bound_params:
            auth_message = f"Parameter(s) `{', '.join(auth_bound_params)}` require authentication and cannot be bound."
            if self.__strict:
                raise ValueError(auth_message)
            warn(auth_message)

    def __copy(
        self,
        session: Optional[ClientSession] = None,
        base_url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Sequence[ParameterSchema]] = None,
        auth_service_token_getters: Optional[Mapping[str, Callable[[], str]]] = None,
        bound_params: Optional[Mapping[str, Union[Callable[[], Any], Any]]] = None,
        strict: Optional[bool] = None,
        original_params: Optional[Sequence[ParameterSchema]] = None,
        original_required_authn_params: Optional[Mapping[str, list[str]]] = None,
    ) -> "ToolboxTool":
        """
        Creates a copy of the ToolboxTool, overriding specific fields.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            description: The description of the remote tool.
            params: The args of the tool.
            auth_service_token_getters: A dict of authService -> token (or callables
                that produce a token)
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            strict: The strictness setting of the tool.
            original_params:
            original_required_authn_params:
        """
        check = lambda val, default: val if val is not None else default

        # Ensure original state and strictness are passed correctly using current values as default
        new_strict = check(strict, self.__strict)
        new_original_params = check(
            original_params, self.__original_params
        )
        new_original_required_authn_params = check(
            original_required_authn_params, self.__original_required_authn_params
        )

        # The 'params' arg here should be the *new* set of *current* (unbound) parameters
        # determined by the calling method (e.g., bind_parameters derives this)
        current_params = check(
            params, self.__params
        )  # This holds the filtered list for the new instance

        # Use current values as defaults for other potentially changed state
        new_auth_getters = check(
            auth_service_token_getters, self.__auth_service_token_getters
        )
        new_bound_params = check(bound_params, self.__bound_parameters)

        # Re-call constructor. Note: This will re-run validation in __init__ if applicable,
        # but _validate_binding should handle it correctly based on the passed bound_params.
        # Pass the original state explicitly using the internal args.
        return ToolboxTool(
            session=check(session, self.__session),
            base_url=check(base_url, self.__base_url),
            name=check(name, self.__name__),
            description=check(description, self.__description),
            params=current_params,
            auth_service_token_getters=new_auth_getters,
            bound_params=new_bound_params,
            strict=new_strict,
            __original_params=new_original_params,
            __original_required_authn_params=new_original_required_authn_params,
        )

    def _check_invocation_auth(self) -> None:
        """
        Verifies that all parameters requiring authentication have a registered
        token getter before invocation. Internal helper for __call__.
        """
        missing_auth_params: dict[str, list[str]] = (
            {}
        )

        # Check against original requirements for parameters *not currently bound*
        for (
            param_name,
            required_sources,
        ) in self.__original_required_authn_params.items():
            if param_name not in self.__bound_parameters:
                has_auth = False
                if required_sources:
                    for source in required_sources:
                        if source in self.__auth_service_token_getters:
                            has_auth = True
                            break
                if not has_auth:
                    missing_auth_params[param_name] = required_sources

        if missing_auth_params:
            param_details = [
                f"'{name}' (requires one of: {', '.join(srcs)})"
                for name, srcs in missing_auth_params.items()
            ]
            available_sources = list(self.__auth_service_token_getters.keys())
            raise PermissionError(
                f"Tool '{self.__name__}' requires authentication for parameter(s) "
                f"{', '.join(param_details)} which is not configured. "
                f"Available authentication sources: {available_sources or 'None'}."
            )
        # TODO: Add check for tool-level auth here (ie. authRequired).

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Asynchronously calls the remote tool with the provided arguments.
        """
        # 1. Check if all required authentications are satisfied for unbound parameters
        self._check_invocation_auth()

        # 2. Bind provided arguments to signature (for current/unbound params)
        try:
            bound_call_args = self.__signature__.bind(*args, **kwargs)
            bound_call_args.apply_defaults()
            payload = bound_call_args.arguments
        except TypeError as e:
            raise TypeError(f"Argument mismatch for tool '{self.__name__}': {e}") from e

        # 3. Validate argument types using pydantic model (for current/unbound params)
        try:
            # Pydantic model validation ensures correct types for unbound args
            validated_payload = self.__pydantic_model.model_validate(payload)
            # Use validated data (handles defaults, conversions, etc.)
            payload_for_api = validated_payload.model_dump()
        except ValidationError as e:
            raise ValidationError(
                f"Invalid argument types for tool '{self.__name__}':\n{e}"
            ) from e

        # 4. Apply statically bound parameters (resolve callables)
        resolved_bound_params: dict[str, Any] = {}
        for param, value in self.__bound_parameters.items():
            resolved_bound_params[param] = await resolve_value(value)

        # 5. Merge provided validated args with resolved bound args
        # Bound parameters take precedence if somehow passed in kwargs as well (shouldn't happen via signature)
        final_payload = {**payload_for_api, **resolved_bound_params}

        # 6. Create headers for auth services
        headers: dict[str, str] = {}
        for auth_service, token_getter in self.__auth_service_token_getters.items():
            # Include all registered tokens. Server side might ignore unused ones.
            try:
                token = await resolve_value(token_getter)
                if not isinstance(token, str):
                    warn(
                        f"Token getter for auth service '{auth_service}' did not return a string.",
                        UserWarning,
                    )
                    token = str(token)  # Attempt conversion
                headers[f"{auth_service}_token"] = token
            except Exception as e:
                # Fail invocation if a token getter fails
                raise RuntimeError(
                    f"Failed to retrieve token for auth service '{auth_service}': {e}"
                ) from e

        # 7. Make the API call
        async with self.__session.post(
            self.__url,
            json=final_payload,
            headers=headers,
            # Consider adding timeout?
            # timeout=aiohttp.ClientTimeout(total=...)
        ) as resp:
            try:
                # Check content type before assuming JSON
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    body = await resp.json()
                else:
                    # Handle non-JSON response as text
                    text_body = await resp.text()
                    # Log or handle text body appropriately
                    # We still need to check status code below
                    body = {
                        "error": f"Non-JSON response received (Content-Type: {content_type}). Body: {text_body[:500]}..."
                    }

            except Exception as json_error:  # Includes JSONDecodeError
                # Handle cases where response is not valid JSON even if header suggests it
                body = await resp.text()
                body = {
                    "error": f"Failed to decode JSON response (status {resp.status}): {json_error}. Body: {body[:500]}..."
                }

            # Check status code *after* trying to read body
            if not (200 <= resp.status < 300):
                err_msg = f"Error calling tool '{self.__name__}' (status {resp.status})"
                if isinstance(body, dict) and "error" in body:
                    # Use error from JSON payload if available
                    err_msg += f": {body['error']}"
                # No need to add body again if it was already included in body['error'] above
                raise Exception(err_msg)  # Or a more specific HTTPError subclass

        # 8. Return result (assuming successful 2xx response)
        if isinstance(body, dict):
            # Prefer 'result' field if present, otherwise return stringified dict
            return str(body.get("result", body))
        else:
            # Should not happen if status check passed and JSON was decoded, but as fallback
            return str(body)

    def add_auth_token_getters(
        self,
        auth_token_getters: Mapping[str, Callable[[], str]],
    ) -> "ToolboxTool":
        """
        Registers auth token getter functions for specified authentication services.
        Creates and returns a *new* tool instance.
        """
        # Check for duplicates against current getters
        existing_services = self.__auth_service_token_getters.keys()
        incoming_services = auth_token_getters.keys()
        duplicates = existing_services & incoming_services
        if duplicates:
            raise ValueError(
                f"Authentication source(s) `{', '.join(duplicates)}` already registered in tool `{self.__name__}`."
            )

        # Create updated map of getters
        new_getters = types.MappingProxyType(
            {**self.__auth_service_token_getters, **auth_token_getters}
        )

        # Return a new instance using __copy, passing the new getters
        return self.__copy(
            auth_service_token_getters=new_getters,
            # Other state (params, bound_params, originals, strict) remains the same
        )

    def bind_parameters(
        self, bound_params: Mapping[str, Union[Callable[[], Any], Any]]
    ) -> "ToolboxTool":
        """
        Binds parameters to specific values or callables.
        Creates and returns a *new* tool instance. Validation uses the
        instance's `strict` mode.
        """
        if not bound_params:
            return self  # Return self if no parameters are being bound

        # 1. Validate the new bindings against original schema & current state
        self._validate_binding(bound_params, check_already_bound=True)

        # 2. Create the new state
        # New combined dictionary of all bound parameters
        all_bound_params = types.MappingProxyType(
            {**self.__bound_parameters, **bound_params}
        )

        # New list of *current* (unbound) parameters for the copied instance
        new_current_params = tuple(
            p for p in self.__original_params if p.name not in all_bound_params
        )

        # 3. Create the new instance via __copy
        return self.__copy(
            params=new_current_params,  # Pass the filtered list as the new 'current' params
            bound_params=all_bound_params,
            # Other state (auth_getters, originals, strict) remains the same
        )
