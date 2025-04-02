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
from typing import Any, Optional, Type, cast

from pydantic import BaseModel, Field, create_model


class ParameterSchema(BaseModel):
    """
    Schema for a tool parameter.
    """

    name: str
    type: str
    description: str
    authSources: Optional[list[str]] = None
    items: Optional["ParameterSchema"] = None

    def __get_type(self) -> Type:
        if self.type == "string":
            return str
        elif self.type == "integer":
            return int
        elif self.type == "float":
            return float
        elif self.type == "boolean":
            return bool
        elif self.type == "array":
            if self.items is None:
                raise Exception("Unexpected value: type is 'list' but items is None")
            return list[self._items.to_type()]  # type: ignore

        raise ValueError(f"Unsupported schema type: {self.type}")

    def to_param(self) -> Parameter:
        return Parameter(
            self.name,
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=self.__get_type(),
        )


class ToolSchema(BaseModel):
    """
    Schema for a tool.
    """

    description: str
    parameters: list[ParameterSchema]
    authRequired: list[str] = []

    def to_pydantic_model(self) -> Type[BaseModel]:
        """Converts the given manifest schema to a Pydantic BaseModel class."""
        field_definitions = {}
        for field in self.parameters:
            field_definitions[field.name] = cast(
                Any,
                (
                    field.to_param().annotation,
                    Field(description=field.description),
                ),
            )
        return create_model("tool_model", **field_definitions)


class ManifestSchema(BaseModel):
    """
    Schema for the Toolbox manifest.
    """

    serverVersion: str
    tools: dict[str, ToolSchema]
