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


from inspect import Parameter, Signature
from typing import Any

from aiohttp import ClientSession


class ToolboxTool:
    """
    A callable proxy object representing a specific tool on a remote Toolbox server.

    Instances of this class behave like asynchronous functions. When called, they
    send a request to the corresponding tool's endpoint on the Toolbox server with
    the provided arguments.

    It utilizes Python's introspection features (`__name__`, `__doc__`,
    `__signature__`, `__annotations__`) so that standard tools like `help()`
    and `inspect` work as expected.
    """

    __url: str
    __session: ClientSession
    __signature__: Signature

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        name: str,
        desc: str,
        params: list[Parameter],
    ):
        """
        Initializes a callable that will trigger the tool invocation through the Toolbox server.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            desc: The description of the remote tool (used as its docstring).
            params: A list of `inspect.Parameter` objects defining the tool's
                arguments and their types/defaults.
        """

        # used to invoke the toolbox API
        self.__session = session
        self.__url = f"{base_url}/api/tool/{name}/invoke"

        # the following properties are set to help anyone that might inspect it determine
        self.__name__ = name
        self.__doc__ = desc
        self.__signature__ = Signature(parameters=params, return_annotation=str)
        self.__annotations__ = {p.name: p.annotation for p in params}
        # TODO: self.__qualname__ ??

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Asynchronously calls the remote tool with the provided arguments.

        Validates arguments against the tool's signature, then sends them
        as a JSON payload in a POST request to the tool's invoke URL.

        Args:
            *args: Positional arguments for the tool.
            **kwargs: Keyword arguments for the tool.

        Returns:
            The string result returned by the remote tool execution.
        """
        all_args = self.__signature__.bind(*args, **kwargs)
        all_args.apply_defaults()  # Include default values if not provided
        payload = all_args.arguments

        async with self.__session.post(
            self.__url,
            json=payload,
        ) as resp:
            ret = await resp.json()
            if "error" in ret:
                # TODO: better error
                raise Exception(ret["error"])
        return ret.get("result", ret)
