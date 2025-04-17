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

from typing import Any, Callable, Mapping, Union

from langchain_core.tools import BaseTool
from toolbox_core.tool import ToolboxTool as ToolboxCoreTool


# This class is an internal implementation detail and is not exposed to the
# end-user. It should not be used directly by external code. Changes to this
# class will not be considered breaking changes to the public API.
class AsyncToolboxTool(BaseTool):
    """
    A subclass of LangChain's BaseTool that supports features specific to
    Toolbox, like bound parameters and authenticated tools.

    It proxies core functionalities like invocation, adding authentication, and
    binding parameters to the underlying toolbox_core.ToolboxTool, adapting it
    for use within the LangChain ecosystem.
    """

    def __init__(
        self,
        core_tool: ToolboxCoreTool,
    ) -> None:
        """
        Initializes an AsyncToolboxTool instance wrapping the provided core tool.

        Args:
            core_tool: An instance of toolbox_core.ToolboxTool.
        """
        if not isinstance(core_tool, ToolboxCoreTool):
            raise TypeError(
                f"Expected core_tool to be an instance of ToolboxCoreTool, got {type(core_tool)}"
            )

        self.__core_tool = core_tool

        super().__init__(
            name=self.__core_tool.__name__,
            description=self.__core_tool._ToolboxTool__description,
            args_schema=self.__core_tool._ToolboxTool__pydantic_model,
        )

    def _run(self, **kwargs: Any) -> str:
        raise NotImplementedError("Synchronous methods not supported by async tools.")

    async def _arun(self, **kwargs: Any) -> str:
        """
        The coroutine that invokes the tool with the given arguments.

        Args:
            **kwargs: The arguments to the tool.

        Returns:
            The string result from the core tool invocation.

        Raises:
            PermissionError: If required authentication is missing.
            ValidationError: If provided arguments are invalid.
            Exception: For API errors or other issues during invocation.
        """
        return await self.__core_tool(**kwargs)

    def add_auth_tokens(
        self, auth_tokens: Mapping[str, Callable[[], str]]
    ) -> "AsyncToolboxTool":
        """
        Registers functions to retrieve ID tokens for the corresponding
        authentication sources.

        Args:
            auth_tokens: A mapping of authentication source names to functions
                that return the corresponding ID token.

        Returns:
            A new AsyncToolboxTool instance that is a deep copy of the current
            instance, with added auth tokens.

        Raises:
            ValueError: If any of the provided auth parameters is already
                registered.
            ValueError: If any of the provided auth parameters is already bound
                and strict is True.

        """
        new_core_tool = self.__core_tool.add_auth_token_getters(auth_tokens)
        return self.__class__(new_core_tool)

    def add_auth_token(
        self, auth_source: str, get_id_token: Callable[[], str]
    ) -> "AsyncToolboxTool":
        """
        Registers a function to retrieve an ID token for a given authentication
        source.

        Args:
            auth_source: The name of the authentication source.
            get_id_token: A function that returns the ID token.

        Returns:
            A new AsyncToolboxTool instance that is a deep copy of the current
            instance, with added auth token.

        Raises:
            ValueError: If the provided auth parameter is already registered.
            ValueError: If the provided auth parameter is already bound and
                strict is True.
        """
        return self.add_auth_tokens({auth_source: get_id_token})

    def bind_params(
        self, bound_params: Mapping[str, Union[Any, Callable[[], Any]]]
    ) -> "AsyncToolboxTool":
        """
        Registers values or functions to retrieve the value for the
        corresponding bound parameters.

        Args:
            bound_params: A mapping of parameter names to their bound
                values or functions to retrieve the values dynamically.

        Returns:
            A new AsyncToolboxTool instance that is a deep copy of the current
            instance, with added bound params.

        Raises:
            ValueError: If any provided parameter name is already bound.
            ValueError: If `strict` is True and any parameter being bound requires
                        authentication or doesn't exist in the original schema.
            Exception: If a parameter name doesn't exist.
        """
        new_core_tool = self.__core_tool.bind_parameters(bound_params)
        return self.__class__(new_core_tool)

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Any, Callable[[], Any]],
    ) -> "AsyncToolboxTool":
        """
        Registers a value or a function to retrieve the value for a given bound
        parameter.

        Args:
            param_name: The name of the parameter to bind.
            param_value: The value or function for the bound parameter.

        Returns:
            A new AsyncToolboxTool instance that is a deep copy of the current
            instance, with added bound param.

        Raises:
            ValueError: If the provided bound param is already bound.
            ValueError: if the provided bound param is not defined in the tool's
                schema, or requires authentication, and strict is True.
            Exception: If the parameter name doesn't exist.
        """
        return self.bind_params({param_name: param_value})
