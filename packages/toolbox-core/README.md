![logo](../../logo.png)
# GenAI Toolbox Core SDK

[![PyPI version](https://badge.fury.io/py/toolbox-core.svg)](https://badge.fury.io/py/toolbox-core) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This SDK allows you to seamlessly integrate the functionalities of
[Toolbox](https://github.com/googleapis/genai-toolbox) allowing you to load and
use tools defined in the service as standard Python functions within your GenAI
applications.

This simplifies integrating external functionalities (like APIs, databases, or
custom logic) managed by the Toolbox into your workflows, especially those
involving Large Language Models (LLMs).

<!-- TOC ignore:true -->
## Table of Contents
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

## Quickstart

Here's a minimal example to get you started:

```py
import asyncio
from toolbox_core import ToolboxClient

async def main():
    toolbox = ToolboxClient("http://127.0.0.1:5000")
    weather_tool = await toolbox.load_tool("get_weather")
    result = await weather_tool(location="London")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Usage

Import and initialize a Toolbox client.

```py
from toolbox_core import ToolboxClient

# Replace with your Toolbox service's URL
toolbox = ToolboxClient("http://127.0.0.1:5000")
```

All interactions for loading and invoking tools happen through this client.

> [!NOTE]
> * The primary `ToolboxClient` is asynchronous and requires using `await` for
>   loading and invoking tools, as shown in most examples.
> * Asynchronous code needs to run within an event loop (e.g., using
>   `asyncio.run()` or in an async framework). See the [Python `asyncio`
>   documentation](https://docs.python.org/3/library/asyncio-task.html) for more
>   details.
> * If you prefer synchronous execution, refer to the [Synchronous
>   Usage](#synchronous-usage) section below.

## Loading Tools

You can load tools individually or in groups (toolsets) as defined in your
Toolbox service configuration.

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

toolbox = ToolboxSyncClient("http://127.0.0.1:5000")
weather_tool = toolbox.load_tool("get_weather")
result = weather_tool(location="Paris")
print(result)
```

> [!TIP]
> While synchronous invocation is available for convenience, it's generally
> considered best practice to use asynchronous operations (like those provided
> by the default `ToolboxClient` and `ToolboxTool`) for I/O-bound tasks like
> tool invocation. Asynchronous programming allows for cooperative multitasking,
> often leading to better performance and resource utilization, especially in
> applications handling concurrent requests.



## Use with LangGraph

The Toolbox Core SDK integrates smoothly with frameworks like LangGraph,
allowing you to incorporate tools managed by the Toolbox service into your
agentic workflows.

The loaded tools are directly compatible with LangChain/LangGraph expectations
(e.g., for use in `ToolNode` or binding to models).

You can follow the [official
guide](https://langchain-ai.github.io/langgraph/how-tos/tool-calling) with
minimal changes.

```py
from toolbox_core import ToolboxClient
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = await toolbox.load_toolset()
model_with_tools = ChatVertexAI(model="gemini-1.5-pro-002").bind_tools(tools)

def call_model(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow = StateGraph(MessagesState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile()
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

This function's implementation depends entirely on your application's
authentication flow. It might retrieve a token stored securely after user login,
initiate an OAuth flow if needed, or fetch/refresh it from secure storage.

> [!NOTE]
> This function can be either an asynchronous function (`async def`) or a
> synchronous function (`async def`); the SDK will handle calling it
> appropriately.

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
toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = await toolbox.load_tool("my-tool")

auth_tool = tool.add_auth_token_getters({"my_auth": get_auth_token})  # Single token

# OR

multi_auth_tool = tool.add_auth_token_getters({
    "my_auth_1", get_auth_token_1,
    "my_auth_2", get_auth_token_2,
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

toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = await toolbox.load_tool("my-tool")

auth_tool = tool.add_auth_token_getters({"my_auth": get_auth_token})
result = auth_tool(input="some input")
print(result)
```

## Binding Parameter Values

The SDK allows you to pre-set, or "bind", values for specific tool parameters
before the tool is invoked or even passed to an LLM. These bound values are
fixed and will not be requested or modified by the LLM during tool use.

### Why Bind Parameters?

* **Protecting sensitive information:**  API keys, secrets, etc.
* **Enforcing consistency:** Ensuring specific values for certain parameters.
* **Pre-filling known data:**  Providing defaults or context.

> [!IMPORTANT]
> You **do not** need to modify the tool's configuration in the Toolbox service to
> bind parameter values using the SDK.

### Option A: Binding Parameters to a Loaded Tool

Bind values to a tool object *after* it has been loaded. This modifies the
specific tool instance.

```py
toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = await toolbox.load_tool("my-tool")

bound_tool = tool.bind_parameters({"param": "value"})
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
[LICENSE](../../LICENSE) file for details.

# Support

If you encounter issues or have questions, check the existing [GitHub Issues](https://github.com/googleapis/genai-toolbox/issues) for the main Toolbox project.