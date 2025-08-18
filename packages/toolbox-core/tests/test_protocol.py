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
from typing import Any, Optional

import pytest

from toolbox_core.protocol import AdditionalPropertiesSchema, ParameterSchema


def test_parameter_schema_float():
    """Tests ParameterSchema with type 'float'."""
    schema = ParameterSchema(name="price", type="float", description="The item price")
    expected_type = float
    assert schema._ParameterSchema__get_type() == expected_type

    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "price"
    assert param.annotation == expected_type
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD
    assert param.default == Parameter.empty


def test_parameter_schema_boolean():
    """Tests ParameterSchema with type 'boolean'."""
    schema = ParameterSchema(
        name="is_active", type="boolean", description="Activity status"
    )
    expected_type = bool
    assert schema._ParameterSchema__get_type() == expected_type

    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "is_active"
    assert param.annotation == expected_type
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD


def test_parameter_schema_array_string():
    """Tests ParameterSchema with type 'array' containing strings."""
    item_schema = ParameterSchema(name="", type="string", description="")
    schema = ParameterSchema(
        name="tags", type="array", description="List of tags", items=item_schema
    )

    assert schema._ParameterSchema__get_type() == list[str]

    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "tags"
    assert param.annotation == list[str]
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD


def test_parameter_schema_array_integer():
    """Tests ParameterSchema with type 'array' containing integers."""
    item_schema = ParameterSchema(name="", type="integer", description="")
    schema = ParameterSchema(
        name="scores", type="array", description="List of scores", items=item_schema
    )

    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "scores"
    assert param.annotation == list[int]
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD


def test_parameter_schema_array_no_items_error():
    """Tests that 'array' type raises error if 'items' is None."""
    schema = ParameterSchema(
        name="bad_list", type="array", description="List without item type"
    )

    expected_error_msg = "Unexpected value: type is 'array' but items is None"
    with pytest.raises(ValueError, match=expected_error_msg):
        schema._ParameterSchema__get_type()

    with pytest.raises(ValueError, match=expected_error_msg):
        schema.to_param()


def test_parameter_schema_unsupported_type_error():
    """Tests that an unsupported type raises ValueError."""
    unsupported_type = "datetime"
    schema = ParameterSchema(
        name="event_time", type=unsupported_type, description="When it happened"
    )

    expected_error_msg = f"Unsupported schema type: {unsupported_type}"
    with pytest.raises(ValueError, match=expected_error_msg):
        schema._ParameterSchema__get_type()

    with pytest.raises(ValueError, match=expected_error_msg):
        schema.to_param()


def test_parameter_schema_string_optional():
    """Tests an optional ParameterSchema with type 'string'."""
    schema = ParameterSchema(
        name="nickname",
        type="string",
        description="An optional nickname",
        required=False,
    )
    expected_type = Optional[str]

    # Test __get_type()
    assert schema._ParameterSchema__get_type() == expected_type

    # Test to_param()
    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "nickname"
    assert param.annotation == expected_type
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD
    assert param.default is None


def test_parameter_schema_required_by_default():
    """Tests that a parameter is required by default."""
    # 'required' is not specified, so it should default to True.
    schema = ParameterSchema(name="id", type="integer", description="A required ID")
    expected_type = int

    # Test __get_type()
    assert schema._ParameterSchema__get_type() == expected_type

    # Test to_param()
    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "id"
    assert param.annotation == expected_type
    assert param.default == Parameter.empty


def test_parameter_schema_array_optional():
    """Tests an optional ParameterSchema with type 'array'."""
    item_schema = ParameterSchema(name="", type="integer", description="")
    schema = ParameterSchema(
        name="optional_scores",
        type="array",
        description="An optional list of scores",
        items=item_schema,
        required=False,
    )
    expected_type = Optional[list[int]]

    # Test __get_type()
    assert schema._ParameterSchema__get_type() == expected_type

    # Test to_param()
    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "optional_scores"
    assert param.annotation == expected_type
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD
    assert param.default is None


def test_parameter_schema_map_generic():
    """Tests ParameterSchema with a generic 'object' type."""
    schema = ParameterSchema(
        name="metadata",
        type="object",
        description="Some metadata",
        additionalProperties=True,
    )
    expected_type = dict[str, Any]
    assert schema._ParameterSchema__get_type() == expected_type

    param = schema.to_param()
    assert isinstance(param, Parameter)
    assert param.name == "metadata"
    assert param.annotation == expected_type
    assert param.kind == Parameter.POSITIONAL_OR_KEYWORD


def test_parameter_schema_map_typed_string():
    """Tests ParameterSchema with a typed 'object' type (string values)."""
    schema = ParameterSchema(
        name="headers",
        type="object",
        description="HTTP headers",
        additionalProperties=AdditionalPropertiesSchema(type="string"),
    )
    expected_type = dict[str, str]
    assert schema._ParameterSchema__get_type() == expected_type

    param = schema.to_param()
    assert param.annotation == expected_type


def test_parameter_schema_map_typed_integer():
    """Tests ParameterSchema with a typed 'object' type (integer values)."""
    schema = ParameterSchema(
        name="user_scores",
        type="object",
        description="User scores",
        additionalProperties=AdditionalPropertiesSchema(type="integer"),
    )
    expected_type = dict[str, int]
    assert schema._ParameterSchema__get_type() == expected_type
    param = schema.to_param()
    assert param.annotation == expected_type


def test_parameter_schema_map_typed_float():
    """Tests ParameterSchema with a typed 'object' type (float values)."""
    schema = ParameterSchema(
        name="item_prices",
        type="object",
        description="Item prices",
        additionalProperties=AdditionalPropertiesSchema(type="float"),
    )
    expected_type = dict[str, float]
    assert schema._ParameterSchema__get_type() == expected_type
    param = schema.to_param()
    assert param.annotation == expected_type


def test_parameter_schema_map_typed_boolean():
    """Tests ParameterSchema with a typed 'object' type (boolean values)."""
    schema = ParameterSchema(
        name="feature_flags",
        type="object",
        description="Feature flags",
        additionalProperties=AdditionalPropertiesSchema(type="boolean"),
    )
    expected_type = dict[str, bool]
    assert schema._ParameterSchema__get_type() == expected_type
    param = schema.to_param()
    assert param.annotation == expected_type


def test_parameter_schema_map_optional():
    """Tests an optional ParameterSchema with a 'object' type."""
    schema = ParameterSchema(
        name="optional_metadata",
        type="object",
        description="Optional metadata",
        required=False,
        additionalProperties=True,
    )
    expected_type = Optional[dict[str, Any]]
    assert schema._ParameterSchema__get_type() == expected_type
    param = schema.to_param()
    assert param.annotation == expected_type
    assert param.default is None


def test_parameter_schema_map_unsupported_value_type_error():
    """Tests that an unsupported map valueType raises ValueError."""
    unsupported_type = "custom_object"
    schema = ParameterSchema(
        name="custom_data",
        type="object",
        description="Custom data map",
        valueType=unsupported_type,
        additionalProperties=AdditionalPropertiesSchema(type=unsupported_type),
    )
    expected_error_msg = f"Unsupported schema type: {unsupported_type}"
    with pytest.raises(ValueError, match=expected_error_msg):
        schema._ParameterSchema__get_type()
