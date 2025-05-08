# Copyright 2024 Google LLC
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
from typing import Any, Callable, Union

from langchain_core.tools import BaseTool
from toolbox_core.sync_tool import ToolboxSyncTool as ToolboxCoreSyncTool



class ToolboxTool(BaseTool):
    """
    A subclass of LangChain's BaseTool that supports features specific to
    Toolbox, like bound parameters and authenticated tools.
    """

    def __init__(
        self,
        core_sync_tool: ToolboxCoreSyncTool,
    ) -> None:
        """
        Initializes a ToolboxTool instance.

        Args:
            core_sync_tool: The underlying core sync ToolboxTool instance.
        """

        # Due to how pydantic works, we must initialize the underlying
        # BaseTool class before assigning values to member variables.
        super().__init__(
            name=core_sync_tool.__name__,
            description=core_sync_tool.__doc__,
            args_schema=core_sync_tool._ToolboxSyncTool__async_tool._ToolboxTool__pydantic_model,
        )
        self.__core_sync_tool = core_sync_tool

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        return self.__core_sync_tool(**kwargs)

    async def _arun(self, **kwargs: Any) -> dict[str, Any]:
        coro = self.__core_sync_tool._ToolboxSyncTool__async_tool(**kwargs)

        # If a loop has not been provided, attempt to run in current thread.
        if not self.__core_sync_client._ToolboxSyncClient__loop:
            return await coro

        # Otherwise, run in the background thread.
        await asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(coro, self.__core_sync_client._ToolboxSyncTool__loop)
        )


    def add_auth_token_getters(
        self, auth_token_getters: dict[str, Callable[[], str]], strict: bool = True
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
        new_core_sync_tool = self.__core_sync_tool.add_auth_token_getters(auth_token_getters)
        return ToolboxTool(core_sync_tool=new_core_sync_tool)


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
            instance, with added auth token.

        Raises:
            ValueError: If the provided auth parameter is already registered.
        """
        return self.add_auth_token_getters({auth_source: get_id_token})

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
        new_core_sync_tool = self.__core_sync_tool.bind_params(bound_params)
        return ToolboxTool(core_sync_tool=new_core_sync_tool)

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Any, Callable[[], Any]],
        strict: bool = True,
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
