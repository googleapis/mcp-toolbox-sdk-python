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


import asyncio
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    Sequence,
    Type,
    Union,
    cast,
)

from pydantic import BaseModel, Field, create_model

from toolbox_core.protocol import ParameterSchema


def create_func_docstring(description: str, params: Sequence[ParameterSchema]) -> str:
    """Convert tool description and params into its function docstring"""
    docstring = description
    if not params:
        return docstring
    docstring += "\n\nArgs:"
    for p in params:
        annotation = p.to_param().annotation
        docstring += f"\n    {p.name} ({getattr(annotation, '__name__', str(annotation))}): {p.description}"
    return docstring


def identify_auth_requirements(
    req_authn_params: Mapping[str, list[str]],
    req_authz_tokens: Sequence[str],
    auth_service_names: Iterable[str],
) -> tuple[dict[str, list[str]], list[str], set[str]]:
    """
    Identifies authentication parameters and authorization tokens that are still
    required because they are not covered by the provided `auth_service_names`.
    Also returns a set of all authentication/authorization services from
    `auth_service_names` that were found to be matching.

    Args:
        req_authn_params: A mapping of parameter names to lists of required
            authentication services for those parameters.
        req_authz_tokens: A list of strings representing all authorization
            tokens that are required to invoke the current tool.
        auth_service_names: An iterable of authentication/authorization service
            names for which token getters are available.

    Returns:
        A tuple containing:
            - required_authn_params: A new dictionary representing the subset of
              required authentication parameters that are not covered by the
              provided `auth_service_names`.
            - required_authz_tokens: A list of required authorization tokens if
              no service name in `auth_service_names` matches any token in
              `req_authz_tokens`. If any match is found, this list is empty.
            - used_services: A set of service names from `auth_service_names`
              that were found to satisfy at least one authentication parameter's
              requirements or matched one of the `req_authz_tokens`.
    """
    required_authn_params: dict[str, list[str]] = {}
    used_services: set[str] = set()

    # find which of the required authn params are covered by available services.
    for param, services in req_authn_params.items():

        # if we don't have a token_getter for any of the services required by the param,
        # the param is still required
        matched_authn_services = [s for s in services if s in auth_service_names]

        if matched_authn_services:
            used_services.update(matched_authn_services)
        else:
            required_authn_params[param] = services

    # find which of the required authz tokens are covered by available services.
    matched_authz_services = [s for s in auth_service_names if s in req_authz_tokens]
    required_authz_tokens: list[str] = []

    # If a match is found, authorization is met (no remaining required tokens).
    # Otherwise, all `req_authz_tokens` are still required. (Handles empty
    # `req_authz_tokens` correctly, resulting in no required tokens).
    if matched_authz_services:
        used_services.update(matched_authz_services)
    else:
        required_authz_tokens = list(req_authz_tokens)

    return required_authn_params, required_authz_tokens, used_services


def params_to_pydantic_model(
    tool_name: str, params: Sequence[ParameterSchema]
) -> Type[BaseModel]:
    """Converts the given parameters to a Pydantic BaseModel class."""
    field_definitions = {}
    for field in params:

        # Determine the default value based on the 'required' flag.
        # '...' (Ellipsis) signifies a required field in Pydantic.
        # 'None' makes the field optional with a default value of None.
        default_value = ... if field.required else None

        field_definitions[field.name] = cast(
            Any,
            (
                field.to_param().annotation,
                Field(
                    description=field.description,
                    default=default_value,
                ),
            ),
        )
    return create_model(tool_name, **field_definitions)


async def resolve_value(
    source: Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any],
) -> Any:
    """
    Asynchronously or synchronously resolves a given source to its value.

    If the `source` is a coroutine function, it will be awaited.
    If the `source` is a regular callable, it will be called.
    Otherwise (if it's not a callable), the `source` itself is returned directly.

    Args:
        source: The value, a callable returning a value, or a callable
                returning an awaitable value.

    Returns:
        The resolved value.
    """

    if asyncio.iscoroutinefunction(source):
        return await source()
    elif callable(source):
        return source()
    return source
