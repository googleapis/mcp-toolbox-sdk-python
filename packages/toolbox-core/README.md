![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)

# MCP Toolbox Core SDK

[![PyPI version](https://badge.fury.io/py/toolbox-core.svg)](https://badge.fury.io/py/toolbox-core) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/toolbox-core)](https://pypi.org/project/toolbox-core/) [![Coverage Status](https://coveralls.io/repos/github/googleapis/genai-toolbox/badge.svg?branch=main)](https://coveralls.io/github/googleapis/genai-toolbox?branch=main)
 [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This SDK allows you to seamlessly integrate the functionalities of
[Toolbox](https://github.com/googleapis/genai-toolbox) allowing you to load and
use tools defined in the service as standard Python functions within your GenAI
applications.

This simplifies integrating external functionalities (like APIs, databases, or
custom logic) managed by the Toolbox into your workflows, especially those
involving Large Language Models (LLMs).

<!-- TOC ignore:true -->
<!-- TOC -->

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Loading Tools](#loading-tools)
    - [Load a toolset](#load-a-toolset)
    - [Load a single tool](#load-a-single-tool)
- [Invoking Tools](#invoking-tools)
- [Synchronous Usage](#synchronous-usage)
- [Use with LangGraph](#use-with-langgraph)
- [Client to Server Authentication](#client-to-server-authentication)
    - [When is Client-to-Server Authentication Needed?](#when-is-client-to-server-authentication-needed)
    - [How it works](#how-it-works)
    - [Configuration](#configuration)
    - [Authenticating with Google Cloud Servers](#authenticating-with-google-cloud-servers)
    - [Step by Step Guide for Cloud Run](#step-by-step-guide-for-cloud-run)
- [Authenticating Tools](#authenticating-tools)
    - [When is Authentication Needed?](#when-is-authentication-needed)
    - [Supported Authentication Mechanisms](#supported-authentication-mechanisms)
    - [Step 1: Configure Tools in Toolbox Service](#step-1-configure-tools-in-toolbox-service)
    - [Step 2: Configure SDK Client](#step-2-configure-sdk-client)
        - [Provide an ID Token Retriever Function](#provide-an-id-token-retriever-function)
        - [Option A: Add Authentication to a Loaded Tool](#option-a-add-authentication-to-a-loaded-tool)
        - [Option B: Add Authentication While Loading Tools](#option-b-add-authentication-while-loading-tools)
    - [Complete Authentication Example](#complete-authentication-example)
- [Binding Parameter Values](#binding-parameter-values)
    - [Why Bind Parameters?](#why-bind-parameters)
    - [Option A: Binding Parameters to a Loaded Tool](#option-a-binding-parameters-to-a-loaded-tool)
    - [Option B: Binding Parameters While Loading Tools](#option-b-binding-parameters-while-loading-tools)
    - [Binding Dynamic Values](#binding-dynamic-values)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

<!-- /TOC -->

## Installation

```bash
pip install toolbox-core
```

> [!NOTE]
>
> - The primary `ToolboxClient` is asynchronous and requires using `await` for
>   loading and invoking tools, as shown in most examples.
> - Asynchronous code needs to run within an event loop (e.g., using
>   `asyncio.run()` or in an async framework). See the [Python `asyncio`
>   documentation](https://docs.python.org/3/library/asyncio-task.html) for more
>   details.
> - If you prefer synchronous execution, refer to the [Synchronous
>   Usage](#synchronous-usage) section below.

> [!IMPORTANT]
>
> The `ToolboxClient` (and its synchronous counterpart `ToolboxSyncClient`)
> interacts with network resources using an underlying HTTP client session. You
> should remember to use a context manager or explicitly call `close()` to clean
> up these resources. If you provide your own session, you'll need to close it
> in addition to calling `ToolboxClient.close()`. 

## Quickstart

Here's a minimal example to get you started. Ensure your Toolbox service is
running and accessible.

```py
import asyncio
from toolbox_core import ToolboxClient

async def main():
    # Replace with the actual URL where your Toolbox service is running
    async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
        weather_tool = await toolbox.load_tool("get_weather")
        result = await weather_tool(location="London")
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

> [!TIP]
> For a complete, end-to-end example including setting up the service and using
> an SDK, see the full tutorial: [**Toolbox Quickstart
> Tutorial**](https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart)

> [!IMPORTANT]
> If you initialize `ToolboxClient` without providing an external session and
> cannot use `async with`, you must explicitly close the client using `await
> toolbox.close()` in a `finally` block. This ensures the internally created
> session is closed.
>
>  ```py
>  toolbox = ToolboxClient("http://127.0.0.1:5000")
>  try:
>      # ... use toolbox ...
>  finally:
>      await toolbox.close()
>  ```

## Usage

Import and initialize a Toolbox client, pointing it to the URL of your running
Toolbox service.

```py
from toolbox_core import ToolboxClient

# Replace with your Toolbox service's URL
async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
```

All interactions for loading and invoking tools happen through this client.

> [!NOTE]
> For advanced use cases, you can provide an external `aiohttp.ClientSession`
> during initialization (e.g., `ToolboxClient(url, session=my_session)`). If you
> provide your own session, you are responsible for managing its lifecycle;
> `ToolboxClient` *will not* close it.

> [!IMPORTANT]
> Closing the `ToolboxClient` also closes the underlying network session shared by
> all tools loaded from that client. As a result, any tool instances you have
> loaded will cease to function and will raise an error if you attempt to invoke
> them after the client is closed.

## Loading Tools

You can load tools individually or in groups (toolsets) as defined in your
Toolbox service configuration. Loading a toolset is convenient when working with
multiple related functions, while loading a single tool offers more granular
control.

### Load a toolset

A toolset is a collection of related tools. You can load all tools in a toolset
or a specific one:

```py
# Load all tools
tools = await toolbox.load_toolset()

# Load a specific toolset
tools = await toolbox.load_toolset("my-toolset")
```

### Load a single tool

Loads a specific tool by its unique name. This provides fine-grained control.

```py
tool = await toolbox.load_tool("my-tool")
```

## Invoking Tools

Once loaded, tools behave like awaitable Python functions. You invoke them using
`await` and pass arguments corresponding to the parameters defined in the tool's
configuration within the Toolbox service.

```py
tool = await toolbox.load_tool("my-tool")
result = await tool("foo", bar="baz")
```

> [!TIP]
> For a more comprehensive guide on setting up the Toolbox service itself, which
> you'll need running to use this SDK, please refer to the [Toolbox Quickstart
> Guide](https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart).

## Synchronous Usage

By default, the `ToolboxClient` and the `ToolboxTool` objects it produces behave like asynchronous Python functions, requiring the use of `await`.

If your application primarily uses synchronous code, or you prefer not to manage an asyncio event loop, you can use the synchronous alternatives provided:

* `ToolboxSyncClient`: The synchronous counterpart to `ToolboxClient`.
* `ToolboxSyncTool`: The synchronous counterpart to `ToolboxTool`.

The `ToolboxSyncClient` handles communication with the Toolbox service synchronously and produces `ToolboxSyncTool` instances when you load tools. You do not use the `await` keyword when interacting with these synchronous versions.

```py
from toolbox_core import ToolboxSyncClient

with ToolboxSyncClient("http://127.0.0.1:5000") as toolbox:
    weather_tool = toolbox.load_tool("get_weather")
    result = weather_tool(location="Paris")
    print(result)
```

> [!TIP]
> While synchronous invocation is available for convenience, it's generally
> considered best practice to use asynchronous operations (like those provided
> by the default `ToolboxClient` and `ToolboxTool`) for an I/O-bound task like
> tool invocation. Asynchronous programming allows for cooperative multitasking,
> often leading to better performance and resource utilization, especially in
> applications handling concurrent requests.

## Use with LangGraph

The Toolbox Core SDK integrates smoothly with frameworks like LangGraph,
allowing you to incorporate tools managed by the Toolbox service into your
agentic workflows.

> [!TIP]
> The loaded tools (both async `ToolboxTool` and sync `ToolboxSyncTool`) are
> callable and can often be used directly. However, to ensure parameter
> descriptions from Google-style docstrings are accurately parsed and made
> available to the LLM (via `bind_tools()`) and LangGraph internals, it's
> recommended to wrap the loaded tools using LangChain's
> [`StructuredTool`](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.structured.StructuredTool.html).

Here's a conceptual example adapting the [official LangGraph tool calling
guide](https://langchain-ai.github.io/langgraph/how-tos/tool-calling):

```py
import asyncio
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, BaseMessage
from toolbox_core import ToolboxClient
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain.tools import StructuredTool
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def main():
    async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
        tools = await toolbox.load_toolset()
        wrapped_tools = [StructuredTool.from_function(tool, parse_docstring=True) for tool in tools]
        model_with_tools = ChatVertexAI(model="gemini-2.5-flash").bind_tools(wrapped_tools)
        tool_node = ToolNode(wrapped_tools)

        def call_agent(state: State):
            response = model_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        def should_continue(state: State):
            last_message = state["messages"][-1]
            if last_message.tool_calls:
                return "tools"
            return END

        graph_builder = StateGraph(State)

        graph_builder.add_node("agent", call_agent)
        graph_builder.add_node("tools", tool_node)

        graph_builder.add_edge(START, "agent")
        graph_builder.add_conditional_edges(
            "agent",
            should_continue,
        )
        graph_builder.add_edge("tools", "agent")

        app = graph_builder.compile()

        prompt = "What is the weather in London?"
        inputs = {"messages": [HumanMessage(content=prompt)]}

        print(f"User: {prompt}\n")
        print("--- Streaming Agent Steps ---")

        events = app.stream(
            inputs,
            stream_mode="values",
        )

        for event in events:
            event["messages"][-1].pretty_print()
            print("\n---\n")

asyncio.run(main())
```

## Client to Server Authentication

This section describes how to authenticate the ToolboxClient itself when
connecting to a Toolbox server instance that requires authentication. This is
crucial for securing your Toolbox server endpoint, especially when deployed on
platforms like Cloud Run, GKE,  or any environment where unauthenticated access is restricted.

This client-to-server authentication ensures that the Toolbox server can verify
the identity of the client making the request before any tool is loaded or
called. It is different from [Authenticating Tools](#authenticating-tools),
which deals with providing credentials for specific tools within an already
connected Toolbox session.

### When is Client-to-Server Authentication Needed?

You'll need this type of authentication if your Toolbox server is configured to
deny unauthenticated requests. For example:

- Your Toolbox server is deployed on Cloud Run and configured to "Require authentication."
- Your server is behind an Identity-Aware Proxy (IAP) or a similar
  authentication layer.
- You have custom authentication middleware on your self-hosted Toolbox server.

Without proper client authentication in these scenarios, attempts to connect or
make calls (like `load_tool`) will likely fail with `Unauthorized` errors.

### How it works

The `ToolboxClient` (and `ToolboxSyncClient`) allows you to specify functions
(or coroutines for the async client) that dynamically generate HTTP headers for
every request sent to the Toolbox server. The most common use case is to add an
Authorization header with a bearer token (e.g., a Google ID token).

These header-generating functions are called just before each request, ensuring
that fresh credentials or header values can be used.

### Configuration

You can configure these dynamic headers as seen below:

```python
from toolbox_core import ToolboxClient

async with ToolboxClient("toolbox-url", client_headers={"header1": header1_getter, "header2": header2_getter, ...}) as client:
    # Use client
    pass
```

### Authenticating with Google Cloud Servers

For Toolbox servers hosted on Google Cloud (e.g., Cloud Run) and requiring
`Google ID token` authentication, the helper module
[auth_methods](src/toolbox_core/auth_methods.py) provides utility functions.

### Step by Step Guide for Cloud Run

1. **Configure Permissions**: [Grant](https://cloud.google.com/run/docs/securing/managing-access#service-add-principals) the `roles/run.invoker` IAM role on the Cloud
   Run service to the principal. This could be your `user account email` or a
   `service account`.
2. **Configure Credentials**
    - Local Development: Set up
   [ADC](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).
    - Google Cloud Environments: When running within Google Cloud (e.g., Compute
      Engine, GKE, another Cloud Run service, Cloud Functions), ADC is typically
      configured automatically, using the environment's default service account.
3. **Connect to the Toolbox Server**

    ```python
    from toolbox_core import auth_methods

    auth_token_provider = auth_methods.aget_google_id_token(URL) # can also use sync method
    async with ToolboxClient(
        URL,
        client_headers={"Authorization": auth_token_provider},
    ) as client:
        tools = await client.load_toolset()

        # Now, you can use the client as usual.
    ```

## Authenticating Tools

> [!WARNING]
> **Always use HTTPS** to connect your application with the Toolbox service,
> especially in **production environments** or whenever the communication
> involves **sensitive data** (including scenarios where tools require
> authentication tokens). Using plain HTTP lacks encryption and exposes your
> application and data to significant security risks, such as eavesdropping and
> tampering.

Tools can be configured within the Toolbox service to require authentication,
ensuring only authorized users or applications can invoke them, especially when
accessing sensitive data.

### When is Authentication Needed?

Authentication is configured per-tool within the Toolbox service itself. If a
tool you intend to use is marked as requiring authentication in the service, you
must configure the SDK client to provide the necessary credentials (currently
Oauth2 tokens) when invoking that specific tool.

### Supported Authentication Mechanisms

The Toolbox service enables secure tool usage through **Authenticated Parameters**. For detailed information on how these mechanisms work within the Toolbox service and how to configure them, please refer to [Toolbox Service Documentation - Authenticated Parameters](https://googleapis.github.io/genai-toolbox/resources/tools/#authenticated-parameters)

### Step 1: Configure Tools in Toolbox Service

First, ensure the target tool(s) are configured correctly in the Toolbox service
to require authentication. Refer to the [Toolbox Service Documentation -
Authenticated
Parameters](https://googleapis.github.io/genai-toolbox/resources/tools/#authenticated-parameters)
for instructions.

### Step 2: Configure SDK Client

Your application needs a way to obtain the required Oauth2 token for the
authenticated user. The SDK requires you to provide a function capable of
retrieving this token *when the tool is invoked*.

#### Provide an ID Token Retriever Function

You must provide the SDK with a function (sync or async) that returns the
necessary token when called. The implementation depends on your application's
authentication flow (e.g., retrieving a stored token, initiating an OAuth flow).

> [!IMPORTANT]
> The name used when registering the getter function with the SDK (e.g.,
> `"my_api_token"`) must exactly match the `name` of the corresponding
> `authServices` defined in the tool's configuration within the Toolbox service.

```py
async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder
```

> [!TIP]
> Your token retriever function is invoked every time an authenticated parameter
> requires a token for a tool call. Consider implementing caching logic within
> this function to avoid redundant token fetching or generation, especially for
> tokens with longer validity periods or if the retrieval process is
> resource-intensive.

#### Option A: Add Authentication to a Loaded Tool

You can add the token retriever function to a tool object *after* it has been
loaded. This modifies the specific tool instance.

```py
async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
    tool = await toolbox.load_tool("my-tool")

    auth_tool = tool.add_auth_token_getter("my_auth", get_auth_token)  # Single token

    # OR

    multi_auth_tool = tool.add_auth_token_getters({
        "my_auth_1": get_auth_token_1,
        "my_auth_2": get_auth_token_2,
    })  # Multiple tokens
```

#### Option B: Add Authentication While Loading Tools

You can provide the token retriever(s) directly during the `load_tool` or
`load_toolset` calls. This applies the authentication configuration only to the
tools loaded in that specific call, without modifying the original tool objects
if they were loaded previously.

```py
auth_tool = await toolbox.load_tool(auth_token_getters={"my_auth": get_auth_token})

# OR

auth_tools = await toolbox.load_toolset(auth_token_getters={"my_auth": get_auth_token})
```

> [!NOTE]
> Adding auth tokens during loading only affect the tools loaded within that
> call.

### Complete Authentication Example

```py
import asyncio
from toolbox_core import ToolboxClient

async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder

async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
    tool = await toolbox.load_tool("my-tool")

    auth_tool = tool.add_auth_token_getters({"my_auth": get_auth_token})
    result = auth_tool(input="some input")
    print(result)
```

> [!NOTE]
> An auth token getter for a specific name (e.g., "GOOGLE_ID") will replace any
> client header with the same name followed by "_token" (e.g.,
> "GOOGLE_ID_token").

## Binding Parameter Values

The SDK allows you to pre-set, or "bind", values for specific tool parameters
before the tool is invoked or even passed to an LLM. These bound values are
fixed and will not be requested or modified by the LLM during tool use.

### Why Bind Parameters?

- **Protecting sensitive information:**  API keys, secrets, etc.
- **Enforcing consistency:** Ensuring specific values for certain parameters.
- **Pre-filling known data:**  Providing defaults or context.

> [!IMPORTANT]
> The parameter names used for binding (e.g., `"api_key"`) must exactly match the
> parameter names defined in the tool's configuration within the Toolbox
> service.

> [!NOTE]
> You do not need to modify the tool's configuration in the Toolbox service to
> bind parameter values using the SDK.

### Option A: Binding Parameters to a Loaded Tool

Bind values to a tool object *after* it has been loaded. This modifies the
specific tool instance.

```py
async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
    tool = await toolbox.load_tool("my-tool")

    bound_tool = tool.bind_param("param", "value")

    # OR

    bound_tool = tool.bind_params({"param": "value"})
```

### Option B: Binding Parameters While Loading Tools

Specify bound parameters directly when loading tools. This applies the binding
only to the tools loaded in that specific call.

```py
bound_tool = await toolbox.load_tool("my-tool", bound_params={"param": "value"})

# OR

bound_tools = await toolbox.load_toolset(bound_params={"param": "value"})
```

> [!NOTE]
> Bound values during loading only affect the tools loaded in that call.

### Binding Dynamic Values

Instead of a static value, you can bind a parameter to a synchronous or
asynchronous function. This function will be called *each time* the tool is
invoked to dynamically determine the parameter's value at runtime.

```py
async def get_dynamic_value():
    # Logic to determine the value
    return "dynamic_value"

dynamic_bound_tool = tool.bind_param("param", get_dynamic_value)
```

> [!IMPORTANT]
> You don't need to modify tool configurations to bind parameter values.

# Contributing

Contributions are welcome! Please refer to the [DEVELOPER.md](./DEVELOPER.md)
file for guidelines on how to set up a development environment and run tests.

# License

This project is licensed under the Apache License 2.0. See the
[LICENSE](https://github.com/googleapis/genai-toolbox/blob/main/LICENSE) file for details.

# Support

If you encounter issues or have questions, check the existing [GitHub Issues](https://github.com/googleapis/genai-toolbox/issues) for the main Toolbox project.
