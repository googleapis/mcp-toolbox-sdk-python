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
from enum import Enum
from inspect import Parameter
from typing import Any, Optional, Type, Union

from pydantic import BaseModel


class Protocol(str, Enum):
    """Defines how the client should choose between communication protocols."""

    MCP_v20250618 = "2025-06-18"
    MCP_v20250326 = "2025-03-26"
    MCP_v20241105 = "2024-11-05"
    MCP_v20251125 = "2025-11-25"
    MCP = MCP_v20250618
    MCP_LATEST = MCP_v20251125

    @staticmethod
    def get_supported_mcp_versions() -> list[str]:
        """Returns a list of supported MCP protocol versions."""
        return [
            Protocol.MCP_v20251125.value,
            Protocol.MCP_v20250618.value,
            Protocol.MCP_v20250326.value,
            Protocol.MCP_v20241105.value,
        ]


__TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
}


def _get_python_type(type_name: str) -> Type:
    """
    A helper function to convert a schema type string to a Python type.
    """
    try:
        return __TYPE_MAP[type_name]
    except KeyError:
        raise ValueError(f"Unsupported schema type: {type_name}")


class AdditionalPropertiesSchema(BaseModel):
    """
    Defines the value type for 'object' parameters.
    """

    type: str

    def get_value_type(self) -> Type:
        """Converts the string type to a Python type."""
        return _get_python_type(self.type)


class ParameterSchema(BaseModel):
    """
    Schema for a tool parameter.
    """

    name: str
    type: str
    required: bool = True
    description: str
    authSources: Optional[list[str]] = None
    items: Optional["ParameterSchema"] = None
    additionalProperties: Optional[Union[bool, AdditionalPropertiesSchema]] = None
    default: Optional[Any] = None

    def get_python_safe_field_name(self) -> str:
        """
        Returns a Python-safe identifier for this parameter name.

        Some parameter names (for example HTTP header names like "X-Application-ID")
        are not valid Python identifiers and cannot be used directly in function
        signatures or introspection utilities. This helper converts such names into
        a safe form by:
        - Replacing non-alphanumeric characters with underscores.
        - Prefixing with 'param_' if the result starts with a digit or is empty.
        """
        name = self.name
        if name.isidentifier():
            return name

        # Replace any non-alphanumeric/underscore character with underscore.
        sanitized = "".join(
            ch if (ch.isalnum() or ch == "_") else "_" for ch in name
        )

        # Ensure the identifier does not start with a digit and is non-empty.
        if not sanitized or sanitized[0].isdigit():
            sanitized = f"param_{sanitized}" if sanitized else "param_"

        return sanitized

    @property
    def has_default(self) -> bool:
        """Returns True if `default` was explicitly provided in schema input."""
        return "default" in self.model_fields_set

    def __get_type(self) -> Type:
        base_type: Type
        if self.type == "array":
            if self.items is None:
                base_type = list[Any]
            else:
                base_type = list[self.items.__get_type()]  # type: ignore
        elif self.type == "object":
            if isinstance(self.additionalProperties, AdditionalPropertiesSchema):
                value_type = self.additionalProperties.get_value_type()
                base_type = dict[str, value_type]  # type: ignore
            else:
                base_type = dict[str, Any]
        else:
            base_type = _get_python_type(self.type)

        if not self.required:
            return Optional[base_type]  # type: ignore

        return base_type

    def to_param(self) -> Parameter:
        default_value: Any = Parameter.empty
        if not self.required:
            # Keep optional function signatures stable: optional inputs default to None,
            # even when schema includes a backend-side default.
            default_value = None
        elif self.has_default:
            default_value = self.default

        return Parameter(
            self.get_python_safe_field_name(),
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=self.__get_type(),
            default=default_value,
        )


class ToolSchema(BaseModel):
    """
    Schema for a tool.
    """

    description: str
    parameters: list[ParameterSchema]
    authRequired: list[str] = []


class ManifestSchema(BaseModel):
    """
    Schema for the Toolbox manifest.
    """

    serverVersion: str
    tools: dict[str, ToolSchema]
