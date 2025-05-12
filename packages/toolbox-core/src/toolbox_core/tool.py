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

import copy
from inspect import Signature
from types import MappingProxyType
from typing import Any, Callable, Coroutine, Mapping, Optional, Sequence, Union

from aiohttp import ClientSession

from .protocol import ParameterSchema
from .utils import (
    create_func_docstring,
    identify_required_authn_params,
    params_to_pydantic_model,
    resolve_value,
)


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

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        name: str,
        description: str,
        params: Sequence[ParameterSchema],
        required_authn_params: Mapping[str, list[str]],
        auth_service_token_getters: Mapping[str, Callable[[], str]],
        bound_params: Mapping[str, Union[Callable[[], Any], Any]],
        client_headers: Mapping[str, Union[Callable, Coroutine, str]],
    ):
        """
        Initializes a callable that will trigger the tool invocation through the
        Toolbox server.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            description: The description of the remote tool.
            params: The args of the tool.
            required_authn_params: A map of required authenticated parameters to a list
                of alternative services that can provide values for them.
            auth_service_token_getters: A dict of authService -> token (or callables that
                produce a token)
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            client_headers: Client specific headers bound to the tool.
        """
        # used to invoke the toolbox API
        self.__session: ClientSession = session
        self.__base_url: str = base_url
        self.__url = f"{base_url}/api/tool/{name}/invoke"
        self.__description = description
        self.__params = params
        self.__pydantic_model = params_to_pydantic_model(name, self.__params)

        inspect_type_params = [param.to_param() for param in self.__params]

        # the following properties are set to help anyone that might inspect it determine usage
        self.__name__ = name
        self.__doc__ = create_func_docstring(self.__description, self.__params)
        self.__signature__ = Signature(
            parameters=inspect_type_params, return_annotation=str
        )

        self.__annotations__ = {p.name: p.annotation for p in inspect_type_params}
        self.__qualname__ = f"{self.__class__.__qualname__}.{self.__name__}"

        # Validate conflicting Headers/Auth Tokens
        request_header_names = client_headers.keys()
        auth_token_names = [
            auth_token_name + "_token"
            for auth_token_name in auth_service_token_getters.keys()
        ]
        duplicates = request_header_names & auth_token_names
        if duplicates:
            raise ValueError(
                f"Client header(s) `{', '.join(duplicates)}` already registered in client. "
                f"Cannot register client the same headers in the client as well as tool."
            )

        # map of parameter name to auth service required by it
        self.__required_authn_params = required_authn_params
        # map of authService -> token_getter
        self.__auth_service_token_getters = auth_service_token_getters
        # map of parameter name to value (or callable that produces that value)
        self.__bound_parameters = bound_params
        # map of client headers to their value/callable/coroutine
        self.__client_headers = client_headers

    @property
    def _name(self) -> str:
        return self.__name__

    @property
    def _description(self) -> str:
        return self.__description

    @property
    def _params(self) -> Sequence[ParameterSchema]:
        return copy.deepcopy(self.__params)

    @property
    def _bound_params(self) -> Mapping[str, Union[Callable[[], Any], Any]]:
        return MappingProxyType(self.__bound_parameters)

    @property
    def _required_auth_params(self) -> Mapping[str, list[str]]:
        return MappingProxyType(self.__required_authn_params)

    @property
    def _auth_service_token_getters(self) -> Mapping[str, Callable[[], str]]:
        return MappingProxyType(self.__auth_service_token_getters)

    @property
    def _client_headers(self) -> Mapping[str, Union[Callable, Coroutine, str]]:
        return MappingProxyType(self.__client_headers)

    def __copy(
        self,
        session: Optional[ClientSession] = None,
        base_url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Sequence[ParameterSchema]] = None,
        required_authn_params: Optional[Mapping[str, list[str]]] = None,
        auth_service_token_getters: Optional[Mapping[str, Callable[[], str]]] = None,
        bound_params: Optional[Mapping[str, Union[Callable[[], Any], Any]]] = None,
        client_headers: Optional[Mapping[str, Union[Callable, Coroutine, str]]] = None,
    ) -> "ToolboxTool":
        """
        Creates a copy of the ToolboxTool, overriding specific fields.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            description: The description of the remote tool.
            params: The args of the tool.
            required_authn_params: A map of required authenticated parameters to a list
                of alternative services that can provide values for them.
            auth_service_token_getters: A dict of authService -> token (or callables
                that produce a token)
            bound_params: A mapping of parameter names to bind to specific values or
                callables that are called to produce values as needed.
            client_headers: Client specific headers bound to the tool.
        """
        check = lambda val, default: val if val is not None else default
        return ToolboxTool(
            session=check(session, self.__session),
            base_url=check(base_url, self.__base_url),
            name=check(name, self.__name__),
            description=check(description, self.__description),
            params=check(params, self.__params),
            required_authn_params=check(
                required_authn_params, self.__required_authn_params
            ),
            auth_service_token_getters=check(
                auth_service_token_getters, self.__auth_service_token_getters
            ),
            bound_params=check(bound_params, self.__bound_parameters),
            client_headers=check(client_headers, self.__client_headers),
        )

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

        # check if any auth services need to be specified yet
        if len(self.__required_authn_params) > 0:
            # Gather all the required auth services into a set
            req_auth_services = set()
            for s in self.__required_authn_params.values():
                req_auth_services.update(s)
            raise Exception(
                f"One or more of the following authn services are required to invoke this tool"
                f": {','.join(req_auth_services)}"
            )

        # validate inputs to this call using the signature
        all_args = self.__signature__.bind(*args, **kwargs)
        all_args.apply_defaults()  # Include default values if not provided
        payload = all_args.arguments

        # Perform argument type validations using pydantic
        self.__pydantic_model.model_validate(payload)

        # apply bounded parameters
        for param, value in self.__bound_parameters.items():
            payload[param] = await resolve_value(value)

        # create headers for auth services
        headers = {}
        for auth_service, token_getter in self.__auth_service_token_getters.items():
            headers[f"{auth_service}_token"] = await resolve_value(token_getter)
        for client_header_name, client_header_val in self.__client_headers.items():
            headers[client_header_name] = await resolve_value(client_header_val)

        async with self.__session.post(
            self.__url,
            json=payload,
            headers=headers,
        ) as resp:
            body = await resp.json()
            if resp.status < 200 or resp.status >= 300:
                err = body.get("error", f"unexpected status from server: {resp.status}")
                raise Exception(err)
        return body.get("result", body)

    def add_auth_token_getters(
        self,
        auth_token_getters: Mapping[str, Callable[[], str]],
    ) -> "ToolboxTool":
        """
        Registers an auth token getter function that is used for AuthServices when tools
        are invoked.

        Args:
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.

        Returns:
            A new ToolboxTool instance with the specified authentication token
            getters registered.

        Raises
            ValueError: If the auth source has already been registered either
            to the tool or to the corresponding client.
        """

        # throw an error if the authentication source is already registered
        existing_services = self.__auth_service_token_getters.keys()
        incoming_services = auth_token_getters.keys()
        duplicates = existing_services & incoming_services
        if duplicates:
            raise ValueError(
                f"Authentication source(s) `{', '.join(duplicates)}` already registered in tool `{self.__name__}`."
            )

        # Validate duplicates with client headers
        request_header_names = self.__client_headers.keys()
        auth_token_names = [
            auth_token_name + "_token" for auth_token_name in incoming_services
        ]
        duplicates = request_header_names & auth_token_names
        if duplicates:
            raise ValueError(
                f"Client header(s) `{', '.join(duplicates)}` already registered in client. "
                f"Cannot register client the same headers in the client as well as tool."
            )

        # create a read-only updated value for new_getters
        new_getters = MappingProxyType(
            dict(self.__auth_service_token_getters, **auth_token_getters)
        )
        # create a read-only updated for params that are still required
        new_req_authn_params = MappingProxyType(
            identify_required_authn_params(
                self.__required_authn_params, auth_token_getters.keys()
            )[0]
        )

        return self.__copy(
            auth_service_token_getters=new_getters,
            required_authn_params=new_req_authn_params,
        )

    def bind_parameters(
        self, bound_params: Mapping[str, Union[Callable[[], Any], Any]]
    ) -> "ToolboxTool":
        """
        Binds parameters to values or callables that produce values.

         Args:
             bound_params: A mapping of parameter names to values or callables that
                 produce values.

         Returns:
             A new ToolboxTool instance with the specified parameters bound.
        """
        param_names = set(p.name for p in self.__params)
        for name in bound_params.keys():
            if name in self.__bound_parameters:
                raise ValueError(
                    f"cannot re-bind parameter: parameter '{name}' is already bound"
                )

            if name not in param_names:
                raise Exception(f"unable to bind parameters: no parameter named {name}")

        new_params = []
        for p in self.__params:
            if p.name not in bound_params:
                new_params.append(p)
        all_bound_params = dict(self.__bound_parameters)
        all_bound_params.update(bound_params)

        return self.__copy(
            params=new_params,
            bound_params=MappingProxyType(all_bound_params),
        )
