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

from inspect import Parameter
from typing import Any, Optional, Type, Union

from pydantic import BaseModel

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

    def __get_type(self) -> Type:
        base_type: Type
        if self.type == "array":
            if self.items is None:
                raise ValueError("Unexpected value: type is 'array' but items is None")
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
        return Parameter(
            self.name,
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=self.__get_type(),
            default=Parameter.empty if self.required else None,
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
