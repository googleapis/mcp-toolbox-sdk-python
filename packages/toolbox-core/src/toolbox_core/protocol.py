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
from typing import Optional, Type

from pydantic import BaseModel


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

    def __get_type(self) -> Type:
        base_type: Type
        if self.type == "string":
            base_type = str
        elif self.type == "integer":
            base_type = int
        elif self.type == "float":
            base_type = float
        elif self.type == "boolean":
            base_type = bool
        elif self.type == "array":
            if self.items is None:
                raise Exception("Unexpected value: type is 'list' but items is None")
            base_type = list[self.items.__get_type()]  # type: ignore
        else:
            raise ValueError(f"Unsupported schema type: {self.type}")

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
