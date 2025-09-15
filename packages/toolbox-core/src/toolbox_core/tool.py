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
import itertools
from collections import OrderedDict
from inspect import Signature
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence, Union
from warnings import warn

from aiohttp import ClientSession

from .protocol import ParameterSchema
from .utils import (
    identify_auth_requirements,
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
        required_authz_tokens: Sequence[str],
        auth_service_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ],
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ],
        client_headers: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]
        ],
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
            required_authn_params: A map of required authenticated parameters to
                a list of alternative services that can provide values for them.
            required_authz_tokens: A sequence of alternative services for
                providing authorization token for the tool invocation.
            auth_service_token_getters: A dict of authService -> token (or
                callables that produce a token)
            bound_params: A mapping of parameter names to bind to specific
                values or callables that are called to produce values as needed.
            client_headers: Client specific headers bound to the tool.
        """
        # used to invoke the toolbox API
        self.__session: ClientSession = session
        self.__base_url: str = base_url
        self.__url = f"{base_url}/api/tool/{name}/invoke"
        self.__description = description
        self.__params = params
        self.__pydantic_model = params_to_pydantic_model(name, self.__params)

        # Separate parameters into required (no default) and optional (with
        # default) to prevent the "non-default argument follows default
        # argument" error when creating the function signature.
        required_params = (p for p in self.__params if p.required)
        optional_params = (p for p in self.__params if not p.required)
        ordered_params = itertools.chain(required_params, optional_params)
        inspect_type_params = [param.to_param() for param in ordered_params]

        # the following properties are set to help anyone that might inspect it determine usage
        self.__name__ = name
        self.__doc__ = self.__description
        self.__signature__ = Signature(
            parameters=inspect_type_params, return_annotation=str
        )

        self.__annotations__ = {p.name: p.annotation for p in inspect_type_params}
        self.__qualname__ = f"{self.__class__.__qualname__}.{self.__name__}"

        # map of parameter name to auth service required by it
        self.__required_authn_params = required_authn_params
        # sequence of authorization tokens required by it
        self.__required_authz_tokens = required_authz_tokens
        # map of authService -> token_getter
        self.__auth_service_token_getters = auth_service_token_getters
        # map of parameter name to value (or callable that produces that value)
        self.__bound_parameters = bound_params
        # map of client headers to their value/callable/coroutine
        self.__client_headers = client_headers

        # ID tokens contain sensitive user information (claims). Transmitting
        # these over HTTP exposes the data to interception and unauthorized
        # access. Always use HTTPS to ensure secure communication and protect
        # user privacy.
        if (
            required_authn_params or required_authz_tokens or client_headers
        ) and not self.__url.startswith("https://"):
            warn(
                "Sending ID token over HTTP. User data may be exposed. Use HTTPS for secure communication."
            )

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
    def _bound_params(
        self,
    ) -> Mapping[str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]]:
        return MappingProxyType(self.__bound_parameters)

    @property
    def _required_authn_params(self) -> Mapping[str, list[str]]:
        return MappingProxyType(self.__required_authn_params)

    @property
    def _required_authz_tokens(self) -> Sequence[str]:
        return tuple(self.__required_authz_tokens)

    @property
    def _auth_service_token_getters(
        self,
    ) -> Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]]]]:
        return MappingProxyType(self.__auth_service_token_getters)

    @property
    def _client_headers(
        self,
    ) -> Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]:
        return MappingProxyType(self.__client_headers)

    def __copy(
        self,
        session: Optional[ClientSession] = None,
        base_url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[Sequence[ParameterSchema]] = None,
        required_authn_params: Optional[Mapping[str, list[str]]] = None,
        required_authz_tokens: Optional[Sequence[str]] = None,
        auth_service_token_getters: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]]]]
        ] = None,
        bound_params: Optional[
            Mapping[str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]]
        ] = None,
        client_headers: Optional[
            Mapping[str, Union[Callable[[], str], Callable[[], Awaitable[str]], str]]
        ] = None,
    ) -> "ToolboxTool":
        """
        Creates a copy of the ToolboxTool, overriding specific fields.

        Args:
            session: The `aiohttp.ClientSession` used for making API requests.
            base_url: The base URL of the Toolbox server API.
            name: The name of the remote tool.
            description: The description of the remote tool.
            params: The args of the tool.
            required_authn_params: A map of required authenticated parameters to
                a list of alternative services that can provide values for them.
            required_authz_tokens: A sequence of alternative services for
                providing authorization token for the tool invocation.
            auth_service_token_getters: A dict of authService -> token (or
                callables that produce a token)
            bound_params: A mapping of parameter names to bind to specific
                values or callables that are called to produce values as needed.
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
            required_authz_tokens=check(
                required_authz_tokens, self.__required_authz_tokens
            ),
            auth_service_token_getters=check(
                auth_service_token_getters, self.__auth_service_token_getters
            ),
            bound_params=check(bound_params, self.__bound_parameters),
            client_headers=check(client_headers, self.__client_headers),
        )

    def __get_auth_header(self, auth_token_name: str) -> str:
        """Returns the formatted auth token header name."""
        return f"{auth_token_name}_token"

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
        if (
            len(self.__required_authn_params) > 0
            or len(self.__required_authz_tokens) > 0
        ):
            # Gather all the required auth services into a set
            req_auth_services = set()
            for s in self.__required_authn_params.values():
                req_auth_services.update(s)
            req_auth_services.update(self.__required_authz_tokens)
            raise PermissionError(
                f"One or more of the following authn services are required to invoke this tool"
                f": {','.join(req_auth_services)}"
            )

        # validate inputs to this call using the signature
        all_args = self.__signature__.bind(*args, **kwargs)

        # The payload will only contain arguments explicitly provided by the user.
        # Optional arguments not provided by the user will not be in the payload.
        payload = all_args.arguments

        # Perform argument type validations using pydantic
        self.__pydantic_model.model_validate(payload)

        # apply bounded parameters
        for param, value in self.__bound_parameters.items():
            payload[param] = await resolve_value(value)

        # Remove None values to prevent server-side type errors. The Toolbox
        # server requires specific types for each parameter and will raise an
        # error if it receives a None value, which it cannot convert.
        payload = OrderedDict({k: v for k, v in payload.items() if v is not None})

        # create headers for auth services
        headers = {}
        for client_header_name, client_header_val in self.__client_headers.items():
            headers[client_header_name] = await resolve_value(client_header_val)

        # In case of conflict, override the client header by the auth token getter
        for auth_service, token_getter in self.__auth_service_token_getters.items():
            headers[self.__get_auth_header(auth_service)] = await resolve_value(
                token_getter
            )

        async with self.__session.post(
            self.__url,
            json=payload,
            headers=headers,
        ) as resp:
            body = await resp.json()
            if not resp.ok:
                err = body.get("error", f"unexpected status from server: {resp.status}")
                raise Exception(err)
        return body.get("result", body)

    def add_auth_token_getters(
        self,
        auth_token_getters: Mapping[
            str, Union[Callable[[], str], Callable[[], Awaitable[str]]]
        ],
    ) -> "ToolboxTool":
        """
        Registers auth token getter functions that are used for AuthServices
        when tools are invoked.

        Args:
            auth_token_getters: A mapping of authentication service names to
                callables that return the corresponding authentication token.

        Returns:
            A new ToolboxTool instance with the specified authentication token
            getters registered.

        Raises:
            ValueError: If an auth source has already been registered either to
            the tool or to the corresponding client.
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
            self.__get_auth_header(auth_token_name)
            for auth_token_name in incoming_services
        ]
        duplicates = request_header_names & auth_token_names
        if duplicates:
            raise ValueError(
                f"Client header(s) `{', '.join(duplicates)}` already registered in client. "
                f"Cannot register client the same headers in the client as well as tool."
            )

        new_getters = dict(self.__auth_service_token_getters, **auth_token_getters)

        # find the updated required authn params, authz tokens and the auth
        # token getters used
        new_req_authn_params, new_req_authz_tokens, used_auth_token_getters = (
            identify_auth_requirements(
                self.__required_authn_params,
                self.__required_authz_tokens,
                auth_token_getters.keys(),
            )
        )

        # ensure no auth token getter provided remains unused
        unused_auth = set(incoming_services) - used_auth_token_getters
        if unused_auth:
            raise ValueError(
                f"Authentication source(s) `{', '.join(unused_auth)}` unused by tool `{self.__name__}`."
            )

        return self.__copy(
            # create read-only values for updated getters, params and tokens
            # that are still required
            auth_service_token_getters=MappingProxyType(new_getters),
            required_authn_params=MappingProxyType(new_req_authn_params),
            required_authz_tokens=tuple(new_req_authz_tokens),
        )

    def add_auth_token_getter(
        self,
        auth_source: str,
        get_id_token: Union[Callable[[], str], Callable[[], Awaitable[str]]],
    ) -> "ToolboxTool":
        """
        Registers an auth token getter function that is used for AuthService
        when tools are invoked.

        Args:
            auth_source: The name of the authentication source.
            get_id_token: A function that returns the ID token.

        Returns:
            A new ToolboxTool instance with the specified authentication token
            getter registered.

        Raises:
            ValueError: If the auth source has already been registered either to
            the tool or to the corresponding client.

        """
        return self.add_auth_token_getters({auth_source: get_id_token})

    def bind_params(
        self,
        bound_params: Mapping[
            str, Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any]
        ],
    ) -> "ToolboxTool":
        """
        Binds parameters to values or callables that produce values.

        Args:
            bound_params: A mapping of parameter names to values or callables that
                produce values.

        Returns:
            A new ToolboxTool instance with the specified parameters bound.

        Raises:
            ValueError: If a parameter is already bound or is not defined by the
                tool's definition.

        """
        param_names = set(p.name for p in self.__params)
        for name in bound_params.keys():
            if name in self.__bound_parameters:
                raise ValueError(
                    f"cannot re-bind parameter: parameter '{name}' is already bound"
                )

            if name not in param_names:
                raise ValueError(
                    f"unable to bind parameters: no parameter named {name}"
                )

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

    def bind_param(
        self,
        param_name: str,
        param_value: Union[Callable[[], Any], Callable[[], Awaitable[Any]], Any],
    ) -> "ToolboxTool":
        """
        Binds a parameter to the value or callable that produce the value.

        Args:
            param_name: The name of the bound parameter.
            param_value: The value of the bound parameter, or a callable that
                returns the value.

        Returns:
            A new ToolboxTool instance with the specified parameter bound.

        Raises:
            ValueError: If the parameter is already bound or is not defined by
                the tool's definition.

        """
        return self.bind_params({param_name: param_value})
