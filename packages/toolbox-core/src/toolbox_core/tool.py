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


import warnings
from inspect import Parameter, Signature
from typing import Any, Callable, TypeVar, Union

from aiohttp import ClientSession

T = TypeVar("T", bound="ToolboxTool")


class ToolboxTool:
    """
    A callable proxy object representing a specific tool on a remote Toolbox server.

    Instances of this class behave like asynchronous functions. When called, they
    send a request to the corresponding tool's endpoint on the Toolbox server with
    the provided arguments, including any bound parameters.

    Methods like `bind_param` return *new* instances
    with the added state, ensuring immutability of the original tool object.

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
        bound_params: Union[dict[str, Union[Any, Callable[[], Any]]], None] = None,
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
            bound_params: Pre-existing bound parameters.
        """
        self.__base_url = base_url

        # used to invoke the toolbox API
        self.__session = session
        self.__url = f"{base_url}/api/tool/{name}/invoke"
        self.__original_params = params

        # Store bound params
        self.__bound_params = bound_params or {}

        # Filter out bound parameters from the signature exposed to the user
        visible_params = [p for p in params if p.name not in self.__bound_params]

        # the following properties are set to help anyone that might inspect it determine
        self.__name__ = name
        self.__doc__ = desc
        # The signature only shows non-bound parameters
        self.__signature__ = Signature(parameters=visible_params, return_annotation=str)
        self.__annotations__ = {p.name: p.annotation for p in visible_params}
        # TODO: self.__qualname__ ??

    def _evaluate_param_vals(
        self, params: dict[str, Union[Any, Callable[[], Any]]]
    ) -> dict[str, Any]:
        """
        Evaluate any callable parameter values.

        Iterates through the input dictionary, calling any callable values
        to get their actual result. Non-callable values are kept as is.

        Args:
            params: A dictionary where keys are parameter names
                and values are either static values or callables returning a value.

        Returns:
            A dictionary containing all parameter names with their resolved, static values.

        Raises:
            RuntimeError: If evaluating a callable parameter value fails.
        """
        resolved_parameters: dict[str, Any] = {}
        for param_name, param_value in params.items():
            try:
                resolved_parameters[param_name] = (
                    param_value() if callable(param_value) else param_value
                )
            except Exception as e:
                raise RuntimeError(
                    f"Error evaluating parameter '{param_name}' for tool '{self.__name__}': {e}"
                ) from e
        return resolved_parameters

    def _prepare_arguments(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Evaluates parameters, merges with call arguments, and binds them
        to the tool's full signature.

        Args:
            *args: Positional arguments provided at call time.
            **kwargs: Keyword arguments provided at call time.

        Returns:
            A dictionary of all arguments ready to be sent to the API.

        Raises:
            TypeError: If call-time arguments conflict with bound parameters,
                       or if arguments don't match the tool's signature.
            RuntimeError: If evaluating a bound parameter fails.
        """
        # Check for conflicts between resolved bound params and keyword arguments
        conflicts = self.__bound_params.keys() & kwargs.keys()
        if conflicts:
            raise TypeError(
                f"Tool '{self.__name__}': Cannot provide value during call for already bound argument(s): {', '.join(conflicts)}"
            )

        evaluated_bound_params = self._evaluate_param_vals(self.__bound_params)
        # Merge params with provided keyword arguments
        merged_kwargs = {**evaluated_bound_params, **kwargs}

        # Bind *args and merged_kwargs using the *original* full signature
        full_signature = Signature(
            parameters=self.__original_params, return_annotation=str
        )
        try:
            bound_args = full_signature.bind(*args, **merged_kwargs)
        except TypeError as e:
            raise TypeError(
                f"Argument binding error for tool '{self.__name__}' (check arguments against signature {full_signature} and bound params {list(self.__bound_params.keys())}): {e}"
            ) from e

        # Apply default values for any missing arguments
        bound_args.apply_defaults()
        return bound_args.arguments

    async def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Asynchronously calls the remote tool with the provided arguments and bound parameters.

        Validates arguments against the tool's signature (excluding bound parameters),
        then sends bound parameters and  call arguments as a JSON payload in a POST request to the tool's invoke URL.

        Args:
            *args: Positional arguments for the tool (for non-bound parameters).
            **kwargs: Keyword arguments for the tool (for non-bound parameters).

        Returns:
            The string result returned by the remote tool execution.

        Raises:
            TypeError: If a bound parameter conflicts with a parameter provided at call time.
            Exception: If the remote tool call results in an error.
        """
        arguments_payload = self._prepare_arguments(*args, **kwargs)

        # Make the API call
        async with self.__session.post(
            self.__url,
            json=arguments_payload,
        ) as resp:
            try:
                ret = await resp.json()
            except Exception as e:
                raise Exception(
                    f"Failed to decode JSON response from tool '{self.__name__}': {e}. Status: {resp.status}, Body: {await resp.text()}"
                ) from e

            if resp.status >= 400 or "error" in ret:
                error_detail = ret.get("error", ret) if isinstance(ret, dict) else ret
                raise Exception(
                    f"Tool '{self.__name__}' invocation failed with status {resp.status}: {error_detail}"
                )

        # Handle cases where 'result' might be missing but no explicit error given
        return ret.get(
            "result", str(ret)
        )  # Return string representation if 'result' key missing

    # --- Methods for adding state (return new instances) ---
    def _copy_with_updates(
        self: T,
        *,
        add_bound_params: Union[dict[str, Union[Any, Callable[[], Any]]], None] = None,
    ) -> T:
        """Creates a new instance with updated bound params."""
        new_bound_params = self.__bound_params.copy()
        if add_bound_params:
            new_bound_params.update(add_bound_params)

        return self.__class__(
            session=self.__session,
            base_url=self.__base_url,
            name=self.__name__,
            desc=self.__doc__ or "",
            params=self.__original_params,
            bound_params=new_bound_params,
        )

    def bind_params(
        self: T,
        params_to_bind: dict[str, Union[Any, Callable[[], Any]]],
        strict: bool = True,
    ) -> T:
        """
        Returns a *new* tool instance with the provided parameters bound.

        Bound parameters are pre-filled values or callables that resolve to values
        when the tool is called. They are not part of the signature of the
        returned tool instance.

        Args:
            params_to_bind: A dictionary mapping parameter names to their
                values or callables that return the value.
            strict: If True (default), raises ValueError if attempting to bind
                a parameter that doesn't exist in the original tool signature
                or is already bound in this instance. If False, issues a warning.

        Returns:
            A new ToolboxTool instance with the specified parameters bound.

        Raises:
            ValueError: If strict is True and a parameter name is invalid or
                already bound.
        """
        invalid_params: list[str] = []
        duplicate_params: list[str] = []
        original_param_names = {p.name for p in self.__original_params}

        for name in params_to_bind:
            if name not in original_param_names:
                invalid_params.append(name)
            elif name in self.__bound_params:
                duplicate_params.append(name)

        messages: list[str] = []
        if invalid_params:
            messages.append(
                f"Parameter(s) {', '.join(invalid_params)} do not exist in the signature for tool '{self.__name__}'."
            )
        if duplicate_params:
            messages.append(
                f"Parameter(s) {', '.join(duplicate_params)} are already bound in this instance of tool '{self.__name__}'."
            )

        if messages:
            message = "\n".join(messages)
            if strict:
                raise ValueError(message)
            else:
                warnings.warn(message)
                # Filter out problematic params if not strict
                params_to_bind = {
                    k: v
                    for k, v in params_to_bind.items()
                    if k not in invalid_params and k not in duplicate_params
                }

        if not params_to_bind:
            return self

        return self._copy_with_updates(add_bound_params=params_to_bind)

    def bind_param(
        self: T,
        param_name: str,
        param_value: Union[Any, Callable[[], Any]],
        strict: bool = True,
    ) -> T:
        """
        Returns a *new* tool instance with the provided parameter bound.

        Convenience method for binding a single parameter.

        Args:
            param_name: The name of the parameter to bind.
            param_value: The value or callable for the parameter.
            strict: If True (default), raises ValueError if the parameter name
                is invalid or already bound. If False, issues a warning.

        Returns:
            A new ToolboxTool instance with the specified parameter bound.

        Raises:
            ValueError: If strict is True and the parameter name is invalid or
                already bound.
        """
        return self.bind_params({param_name: param_value}, strict=strict)
