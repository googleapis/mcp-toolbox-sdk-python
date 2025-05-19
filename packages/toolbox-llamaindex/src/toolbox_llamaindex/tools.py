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

from asyncio import to_thread
from typing import Any, Callable, Union

from deprecated import deprecated
from llama_index.core.tools import ToolMetadata
from llama_index.core.tools.types import AsyncBaseTool, ToolOutput
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool
from toolbox_core.utils import params_to_pydantic_model


class ToolboxTool(AsyncBaseTool):
    """
    A subclass of LlamaIndex's AsyncBaseTool that supports features specific to
    Toolbox, like bound parameters and authenticated tools.
    """

    def __init__(
        self,
        core_tool: ToolboxCoreSyncTool,
    ) -> None:
        """
        Initializes a ToolboxTool instance.

        Args:
            core_tool: The underlying core sync ToolboxTool instance.
        """
        # Due to how pydantic works, we must initialize the underlying
        # AsyncBaseTool class before assigning values to member variables.
        super().__init__()

        self.__core_tool = core_tool

    @property
    def metadata(self) -> ToolMetadata:
        if self.__core_tool.__doc__ is None:
            raise ValueError("No description found for the tool.")

        return ToolMetadata(
            name=self.__core_tool.__name__,
            description=self.__core_tool.__doc__,
            fn_schema=params_to_pydantic_model(
                self.__core_tool._name, self.__core_tool._params
            ),
        )

    def call(self, **kwargs: Any) -> ToolOutput:  # type: ignore
        output_content = self.__core_tool(**kwargs)
        return ToolOutput(
            content=output_content,
            tool_name=self.__core_tool.__name__,
            raw_input=kwargs,
            raw_output=output_content,
        )

    async def acall(self, **kwargs: Any) -> ToolOutput:  # type: ignore
        output_content = await to_thread(self.__core_tool, **kwargs)
        return ToolOutput(
            content=output_content,
            tool_name=self.__core_tool.__name__,
            raw_input=kwargs,
            raw_output=output_content,
        )

    def add_auth_token_getters(
        self, auth_token_getters: dict[str, Callable[[], str]]
    ) -> "ToolboxTool":
        """
        Registers functions to retrieve ID tokens for the corresponding
        authentication sources.

        Args:
            auth_token_getters: A dictionary of authentication source names to
                the functions that return corresponding ID token.

        Returns:
            A new ToolboxTool instance that is a deep copy of the current
            instance, with added auth token getters.

        Raises:
            ValueError: If any of the provided auth parameters is already
                registered.
        """
        new_core_tool = self.__core_tool.add_auth_token_getters(auth_token_getters)
        return ToolboxTool(core_tool=new_core_tool)

    def add_auth_token_getter(
        self, auth_source: str, get_id_token: Callable[[], str]
    ) -> "ToolboxTool":
        """
        Registers a function to retrieve an ID token for a given authentication
        source.

        Args:
            auth_source: The name of the authentication source.
            get_id_token: A function that returns the ID token.

        Returns:
            A new ToolboxTool instance that is a deep copy of the current
            instance, with added auth token getter.

        Raises:
            ValueError: If the provided auth parameter is already registered.
        """
        return self.add_auth_token_getters({auth_source: get_id_token})

    @deprecated("Please use `add_auth_token_getters` instead.")
    def add_auth_tokens(
        self, auth_tokens: dict[str, Callable[[], str]], strict: bool = True
    ) -> "ToolboxTool":
        return self.add_auth_token_getters(auth_tokens)

    @deprecated("Please use `add_auth_token_getter` instead.")
    def add_auth_token(
        self, auth_source: str, get_id_token: Callable[[], str], strict: bool = True
    ) -> "ToolboxTool":
        return self.add_auth_token_getter(auth_source, get_id_token)

    def bind_params(
        self,
        bound_params: dict[str, Union[Any, Callable[[], Any]]],
    ) -> "ToolboxTool":
        """
        Registers values or functions to retrieve the value for the
        corresponding bound parameters.

        Args:
            bound_params: A dictionary of the bound parameter name to the
                value or function of the bound value.

        Returns:
            A new ToolboxTool instance that is a deep copy of the current
            instance, with added bound params.

        Raises:
            ValueError: If any of the provided bound params is already bound.
        """
        new_core_tool = self.__core_tool.bind_params(bound_params)
        return ToolboxTool(core_tool=new_core_tool)

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Any, Callable[[], Any]],
    ) -> "ToolboxTool":
        """
        Registers a value or a function to retrieve the value for a given bound
        parameter.

        Args:
            param_name: The name of the bound parameter.
            param_value: The value of the bound parameter, or a callable that
                returns the value.

        Returns:
            A new ToolboxTool instance that is a deep copy of the current
            instance, with added bound param.

        Raises:
            ValueError: If the provided bound param is already bound.
        """
        return self.bind_params({param_name: param_value})
