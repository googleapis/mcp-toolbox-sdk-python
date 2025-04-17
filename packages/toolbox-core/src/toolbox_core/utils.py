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
    Mapping,
    Sequence,
    Type,
    Union,
    cast,
)
from types import MappingProxyType

from pydantic import BaseModel, Field, create_model

from toolbox_core.protocol import ParameterSchema


def create_func_docstring(description: str, params: Sequence[ParameterSchema]) -> str:
    """Convert tool description and params into its function docstring"""
    docstring = description
    if not params:
        return docstring
    docstring += "\n\nArgs:"
    for p in params:
        docstring += (
            f"\n    {p.name} ({p.to_param().annotation.__name__}): {p.description}"
        )
    return docstring


def identify_required_authn_params(
    params: Sequence[ParameterSchema],
) -> Mapping[str, list[str]]:
    """Helper to extract auth requirements from parameter schemas."""
    req_auth: dict[str, list[str]] = {}
    for p in params:
        if hasattr(p, "authSources") and p.authSources:
            req_auth[p.name] = p.authSources
    return MappingProxyType(req_auth)


def params_to_pydantic_model(
    tool_name: str, params: Sequence[ParameterSchema]
) -> Type[BaseModel]:
    """Converts the given parameters to a Pydantic BaseModel class."""
    field_definitions = {}
    for field in params:
        field_definitions[field.name] = cast(
            Any,
            (
                field.to_param().annotation,
                Field(description=field.description),
            ),
        )
    return create_model(tool_name, **field_definitions)


async def resolve_value(
    source: Union[Callable[[], Awaitable[Any]], Callable[[], Any], Any],
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
