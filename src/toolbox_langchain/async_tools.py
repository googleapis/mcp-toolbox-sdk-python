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

from copy import deepcopy
from typing import Any, Callable, TypeVar, Union, Dict, List, Tuple, Type
from warnings import warn
import inspect
import asyncio

from aiohttp import ClientSession
from pydantic import BaseModel, Field, create_model


class AsyncToolboxTool():
    __name: str
    __schema: ToolSchema
    __model: Type[BaseModel]
    __url: str
    __session: ClientSession
    __auth_tokens: Dict[str, Callable[[], str]]
    __auth_params: List[ParameterSchema]
    __bound_params: Dict[str, Union[Any, Callable[[], Any]]]

    def __init__(
        self,
        name: str,
        schema: ToolSchema,
        url: str,
        session: ClientSession,
        auth_tokens: Dict[str, Callable[[], str]] = {},
        bound_params: Dict[str, Union[Any, Callable[[], Any]]] = {},
        strict: bool = True,
    ) -> None:
        auth_params, non_auth_params = _find_auth_params(schema.parameters)
        non_auth_bound_params, non_auth_non_bound_params = _find_bound_params(
            non_auth_params, list(bound_params)
        )

        # Check if the user is trying to bind a param that is authenticated or
        # is missing from the given schema.
        auth_bound_params: List[str] = []
        missing_bound_params: List[str] = []
        for bound_param in bound_params:
            if bound_param in [param.name for param in auth_params]:
                auth_bound_params.append(bound_param)
            elif bound_param not in [param.name for param in non_auth_params]:
                missing_bound_params.append(bound_param)

        # Create error messages for any params that are found to be
        # authenticated or missing.
        messages: List[str] = []
        if auth_bound_params:
            messages.append(
                f"Parameter(s) {', '.join(auth_bound_params)} already authenticated and cannot be bound."
            )
        if missing_bound_params:
            messages.append(
                f"Parameter(s) {', '.join(missing_bound_params)} missing and cannot be bound."
            )

        # Join any error messages and raise them as an error or warning,
        # depending on the value of the strict flag.
        if messages:
            message = "\n\n".join(messages)
            if strict:
                raise ValueError(message)
            warn(message)

        # Bind values for parameters present in the schema that don't require
        # authentication.
        _bound_params = {
            param_name: param_value
            for param_name, param_value in bound_params.items()
            if param_name in [param.name for param in non_auth_bound_params]
        }

        # Update the tools schema to validate only the presence of parameters
        # that neither require authentication nor are bound.
        _updated_schema = deepcopy(schema)
        _updated_schema.parameters = non_auth_non_bound_params

        self.__name = name
        self.__schema = _updated_schema
        self.__model = _schema_to_model(self.__name, self.__schema.parameters)
        self.__url = url
        self.__session = session
        self.__auth_tokens = auth_tokens
        self.__auth_params = auth_params
        self.__bound_params = _bound_params

        # Warn users about any missing authentication so they can add it before
        # tool invocation.
        self.__validate_auth(strict=False)

        # Make the tool instance directly callable.
        docstring = schema_to_docstring(self.__schema, self.__bound_params)

        # Create a list to store parameter definitions for the function signature
        sig_params = []
        for param in self.__schema.parameters:
            # TODO: Change to _parse_type(param) post latest SDK release.
            param_type = _parse_type(param.type)
            sig_params.append(
                inspect.Parameter(
                    param.name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=param_type
                )
            )

        # Create the function signature
        sig = inspect.Signature(parameters=sig_params, return_annotation=Dict[str, Any])
        self.__signature__ = sig
        self.__doc__ = docstring
        self.__name__ = self.__name


    def __validate_auth(self, strict: bool = True) -> None:
        # TODO: Add this once we release the latest SDK code.
        # is_authenticated: bool = not self.__schema.authRequired
        # # Check tool for at least 1 required auth source
        # for src in self.__schema.authRequired:
        #     if src in self.__auth_tokens:
        #         is_authenticated = True
        #         break
        # if not is_authenticated:
        #     messages.append(
        #         f"Tool {self.__name} requires authentication, but no valid authentication sources are registered. Please register the required sources before use."
        #     )

        # Check each parameter for at least 1 required auth source
        params_missing_auth: List[str] = []
        for param in self.__auth_params:
            if not param.authSources:
                raise ValueError("Auth sources cannot be None.")
            has_auth = False
            for src in param.authSources:

                # Find first auth source that is specified
                if src in self.__auth_tokens:
                    has_auth = True
                    break
            if not has_auth:
                params_missing_auth.append(param.name)

        messages: List[str] = []

        if params_missing_auth:
            messages.append(
                f"Parameter(s) `{', '.join(params_missing_auth)}` of tool {self.__name} require authentication, but no valid authentication sources are registered. Please register the required sources before use."
            )

        if messages:
            message = "\n\n".join(messages)
            if strict:
                raise PermissionError(message)
            warn(message)

    def __create_copy(
        self,
        *,
        auth_tokens: Dict[str, Callable[[], str]] = {},
        bound_params: Dict[str, Union[Any, Callable[[], Any]]] = {},
        strict: bool,
    ) -> "AsyncToolboxTool":

        new_schema = deepcopy(self.__schema)

        # Reconstruct the complete parameter schema by merging the auth
        # parameters back with the non-auth parameters. This is necessary to
        # accurately validate the new combination of auth tokens and bound
        # params in the constructor of the new AsyncToolboxTool instance, ensuring
        # that any overlaps or conflicts are correctly identified and reported
        # as errors or warnings, depending on the given `strict` flag.
        new_schema.parameters += self.__auth_params
        return AsyncToolboxTool(
            name=self.__name,
            schema=new_schema,
            url=self.__url,
            session=self.__session,
            auth_tokens={**self.__auth_tokens, **auth_tokens},
            bound_params={**self.__bound_params, **bound_params},
            strict=strict,
        )

    def add_auth_tokens(
        self, auth_tokens: Dict[str, Callable[[], str]], strict: bool = True
    ) -> "AsyncToolboxTool":

        # Check if the authentication source is already registered.
        dupe_tokens: List[str] = []
        for auth_token, _ in auth_tokens.items():
            if auth_token in self.__auth_tokens:
                dupe_tokens.append(auth_token)

        if dupe_tokens:
            raise ValueError(
                f"Authentication source(s) `{', '.join(dupe_tokens)}` already registered in tool `{self.__name}`."
            )

        return self.__create_copy(auth_tokens=auth_tokens, strict=strict)

    def add_auth_token(
        self, auth_source: str, get_id_token: Callable[[], str], strict: bool = True
    ) -> "AsyncToolboxTool":
        return self.add_auth_tokens({auth_source: get_id_token}, strict=strict)

    def bind_params(
        self,
        bound_params: Dict[str, Union[Any, Callable[[], Any]]],
        strict: bool = True,
    ) -> "AsyncToolboxTool":

        # Check if the parameter is already bound.
        dupe_params: List[str] = []
        for param_name, _ in bound_params.items():
            if param_name in self.__bound_params:
                dupe_params.append(param_name)

        if dupe_params:
            raise ValueError(
                f"Parameter(s) `{', '.join(dupe_params)}` already bound in tool `{self.__name}`."
            )

        return self.__create_copy(bound_params=bound_params, strict=strict)

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Any, Callable[[], Any]],
        strict: bool = True,
    ) -> "AsyncToolboxTool":
        return self.bind_params({param_name: param_value}, strict=strict)

    async def __call__(self, *args, **kwargs) -> Any:
        call_args = self.__signature__.bind(*args, **kwargs).arguments
        self.__model.model_validate(call_args)

        # If the tool had parameters that require authentication, then right
        # before invoking that tool, we check whether all these required
        # authentication sources have been registered or not.
        self.__validate_auth()

        # Evaluate dynamic parameter values if any
        evaluated_params = {}
        for param_name, param_value in self.__bound_params.items():
            if callable(param_value):
                evaluated_params[param_name] = param_value()
            else:
                evaluated_params[param_name] = param_value

        # Merge bound parameters with the provided arguments
        call_args.update(evaluated_params)

        return await _invoke_tool(
            self.__url, self.__session, self.__name, call_args, self.__auth_tokens
        )
