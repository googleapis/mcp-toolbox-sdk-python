![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)
# MCP Toolbox LlamaIndex SDK

This SDK allows you to seamlessly integrate the functionalities of
[Toolbox](https://github.com/googleapis/genai-toolbox) into your LlamaIndex LLM
applications, enabling advanced orchestration and interaction with GenAI models.

<!-- TOC ignore:true -->
## Table of Contents
<!-- TOC -->

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Loading Tools](#loading-tools)
    - [Load a toolset](#load-a-toolset)
    - [Load a single tool](#load-a-single-tool)
- [Use with LlamaIndex](#use-with-llamaindex)
    - [Maintain state](#maintain-state)
- [Manual usage](#manual-usage)
- [Authenticating Tools](#authenticating-tools)
    - [Supported Authentication Mechanisms](#supported-authentication-mechanisms)
    - [Configure Tools](#configure-tools)
    - [Configure SDK](#configure-sdk)
        - [Add Authentication to a Tool](#add-authentication-to-a-tool)
        - [Add Authentication While Loading](#add-authentication-while-loading)
    - [Complete Example](#complete-example)
- [Binding Parameter Values](#binding-parameter-values)
    - [Binding Parameters to a Tool](#binding-parameters-to-a-tool)
    - [Binding Parameters While Loading](#binding-parameters-while-loading)
    - [Binding Dynamic Values](#binding-dynamic-values)
- [Asynchronous Usage](#asynchronous-usage)

<!-- /TOC -->

## Installation

```bash
pip install toolbox-llamaindex
```

## Quickstart

Here's a minimal example to get you started using
[LlamaIndex](https://docs.llamaindex.ai/en/stable/#getting-started):

```py
import asyncio

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.agent.workflow import AgentWorkflow

from toolbox_llamaindex import ToolboxClient

async def run_agent():
  toolbox = ToolboxClient("http://127.0.0.1:5000")
  tools = toolbox.load_toolset()

  vertex_model = GoogleGenAI(
      model="gemini-2.0-flash-001",
      vertexai_config={"project": "project-id", "location": "us-central1"},
  )
  agent = AgentWorkflow.from_tools_or_functions(
      tools,
      llm=vertex_model,
      system_prompt="You are a helpful assistant.",
  )
  response = await agent.run(user_msg="Get some response from the agent.")
  print(response)

asyncio.run(run_agent())
```

## Usage

Import and initialize the toolbox client.

```py
from toolbox_llamaindex import ToolboxClient

# Replace with your Toolbox service's URL
toolbox = ToolboxClient("http://127.0.0.1:5000")
```

## Loading Tools

### Load a toolset

A toolset is a collection of related tools. You can load all tools in a toolset
or a specific one:

```py
# Load all tools
tools = toolbox.load_toolset()

# Load a specific toolset
tools = toolbox.load_toolset("my-toolset")
```

### Load a single tool

```py
tool = toolbox.load_tool("my-tool")
```

Loading individual tools gives you finer-grained control over which tools are
available to your LLM agent.

## Use with LlamaIndex

LlamaIndex's agents can dynamically choose and execute tools based on the user
input. Include tools loaded from the Toolbox SDK in the agent's toolkit:

```py
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.agent.workflow import AgentWorkflow

vertex_model = GoogleGenAI(
    model="gemini-2.0-flash-001",
    vertexai_config={"project": "project-id", "location": "us-central1"},
)

# Initialize agent with tools
agent = AgentWorkflow.from_tools_or_functions(
    tools,
    llm=vertex_model,
    system_prompt="You are a helpful assistant.",
)

# Query the agent
response = await agent.run(user_msg="Get some response from the agent.")
print(response)
```

### Maintain state

To maintain state for the agent, add context as follows:

```py
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Context
from llama_index.llms.google_genai import GoogleGenAI

vertex_model = GoogleGenAI(
    model="gemini-2.0-flash-001",
    vertexai_config={"project": "twisha-dev", "location": "us-central1"},
)
agent = AgentWorkflow.from_tools_or_functions(
    tools,
    llm=vertex_model,
    system_prompt="You are a helpful assistant",
)

# Save memory in agent context
ctx = Context(agent)
response = await agent.run(user_msg="Give me some response.", ctx=ctx)
print(response)
```

## Manual usage

Execute a tool manually using the `call` method:

```py
result = tools[0].call(name="Alice", age=30)
```

This is useful for testing tools or when you need precise control over tool
execution outside of an agent framework.

## Authenticating Tools

> [!WARNING]
> Always use HTTPS to connect your application with the Toolbox service,
> especially when using tools with authentication configured. Using HTTP exposes
> your application to serious security risks.

Some tools require user authentication to access sensitive data.

### Supported Authentication Mechanisms
Toolbox currently supports authentication using the [OIDC
protocol](https://openid.net/specs/openid-connect-core-1_0.html) with [ID
tokens](https://openid.net/specs/openid-connect-core-1_0.html#IDToken) (not
access tokens) for [Google OAuth
2.0](https://cloud.google.com/apigee/docs/api-platform/security/oauth/oauth-home).

### Configure Tools

Refer to [these
instructions](https://googleapis.github.io/genai-toolbox/resources/tools/#authenticated-parameters) on
configuring tools for authenticated parameters.

### Configure SDK

You need a method to retrieve an ID token from your authentication service:

```py
async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder
```

#### Add Authentication to a Tool

```py
toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = toolbox.load_toolset()

auth_tool = tools[0].add_auth_token_getter("my_auth", get_auth_token) # Single token

multi_auth_tool = tools[0].add_auth_token_getters({"auth_1": get_auth_1}, {"auth_2": get_auth_2}) # Multiple tokens

# OR

auth_tools = [tool.add_auth_token_getter("my_auth", get_auth_token) for tool in tools]
```

#### Add Authentication While Loading

```py
auth_tool = toolbox.load_tool(auth_token_getters={"my_auth": get_auth_token})

auth_tools = toolbox.load_toolset(auth_token_getters={"my_auth": get_auth_token})
```

> [!NOTE]
> Adding auth tokens during loading only affect the tools loaded within
> that call.

### Complete Example

```py
import asyncio
from toolbox_llamaindex import ToolboxClient

async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder

toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = toolbox.load_tool("my-tool")

auth_tool = tool.add_auth_token_getter("my_auth", get_auth_token)
result = auth_tool.call(input="some input")
print(result)
```

## Binding Parameter Values

Predetermine values for tool parameters using the SDK. These values won't be
modified by the LLM. This is useful for:

* **Protecting sensitive information:**  API keys, secrets, etc.
* **Enforcing consistency:** Ensuring specific values for certain parameters.
* **Pre-filling known data:**  Providing defaults or context.

### Binding Parameters to a Tool

```py
toolbox = ToolboxClient("http://127.0.0.1:5000")
tools = toolbox.load_toolset()

bound_tool = tool[0].bind_param("param", "value") # Single param

multi_bound_tool = tools[0].bind_params({"param1": "value1", "param2": "value2"}) # Multiple params

# OR

bound_tools = [tool.bind_param("param", "value") for tool in tools]
```

### Binding Parameters While Loading

```py
bound_tool = toolbox.load_tool("my-tool", bound_params={"param": "value"})

bound_tools = toolbox.load_toolset(bound_params={"param": "value"})
```

> [!NOTE]
> Bound values during loading only affect the tools loaded in that call.

### Binding Dynamic Values

Use a function to bind dynamic values:

```py
def get_dynamic_value():
  # Logic to determine the value
  return "dynamic_value"

dynamic_bound_tool = tool.bind_param("param", get_dynamic_value)
```

> [!IMPORTANT]
> You don't need to modify tool configurations to bind parameter values.

## Asynchronous Usage

For better performance through [cooperative
multitasking](https://en.wikipedia.org/wiki/Cooperative_multitasking), you can
use the asynchronous interfaces of the `ToolboxClient`.

> [!Note]
> Asynchronous interfaces like `aload_tool` and `aload_toolset` require an
> asynchronous environment. For guidance on running asynchronous Python
> programs, see [asyncio
> documentation](https://docs.python.org/3/library/asyncio-runner.html#running-an-asyncio-program).

```py
import asyncio
from toolbox_llamaindex import ToolboxClient

async def main():
    toolbox = ToolboxClient("http://127.0.0.1:5000")
    tool = await client.aload_tool("my-tool")
    tools = await client.aload_toolset()
    response = await tool.ainvoke()

if __name__ == "__main__":
    asyncio.run(main())
```
