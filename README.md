![MCP Toolbox
Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)
# MCP Toolbox SDKs for Python

[![License: Apache
2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI - Python
Version](https://img.shields.io/pypi/pyversions/toolbox-core)](https://pypi.org/project/toolbox-core/)

This repository contains Python SDKs designed to seamlessly integrate the
functionalities of the [MCP
Toolbox](https://github.com/googleapis/genai-toolbox) into your Gen AI
applications. These SDKs allow you to load tools defined in Toolbox and use them
as standard Python functions or objects within popular orchestration frameworks
or your custom code.

This simplifies the process of incorporating external functionalities (like
Databases or APIs) managed by Toolbox into your GenAI applications.

<!-- TOC -->

- [Overview](#overview)
- [Available Packages](#available-packages)
- [Quickstart](#quickstart)
- [Core Concepts](#core-concepts)
    - [Connecting to Toolbox](#connecting-to-toolbox)
    - [Loading Tools](#loading-tools)
    - [Invoking Tools](#invoking-tools)
    - [Synchronous vs. Asynchronous Usage](#synchronous-vs-asynchronous-usage)
    - [Authenticating Tools](#authenticating-tools)
        - [When is Authentication Needed?](#when-is-authentication-needed)
        - [Supported Authentication Mechanisms](#supported-authentication-mechanisms)
        - [SDK Configuration](#sdk-configuration)
    - [Binding Parameter Values](#binding-parameter-values)
        - [Why Bind Parameters?](#why-bind-parameters)
        - [SDK Configuration](#sdk-configuration)
- [Usage Comparison](#usage-comparison)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

<!-- /TOC -->
## Overview

The Toolbox service provides a centralized way to manage and expose tools for
use by LLMs. <!-- TOC -->

- [MCP Toolbox SDKs for Python](#mcp-toolbox-sdks-for-python)
    - [Overview](#overview)
    - [Available Packages](#available-packages)
    - [Quickstart](#quickstart)
    - [Core Concepts](#core-concepts)
        - [Connecting to Toolbox](#connecting-to-toolbox)
        - [Loading Tools](#loading-tools)
        - [Invoking Tools](#invoking-tools)
        - [Synchronous vs. Asynchronous Usage](#synchronous-vs-asynchronous-usage)
        - [Authenticating Tools](#authenticating-tools)
            - [When is Authentication Needed?](#when-is-authentication-needed)
            - [Supported Authentication Mechanisms](#supported-authentication-mechanisms)
            - [SDK Configuration](#sdk-configuration)
        - [Binding Parameter Values](#binding-parameter-values)
            - [Why Bind Parameters?](#why-bind-parameters)
            - [SDK Configuration](#sdk-configuration)
    - [Usage Comparison](#usage-comparison)
    - [Contributing](#contributing)
    - [License](#license)
    - [Support](#support)

<!-- /TOC -->These SDKs act as clients for that service, abstracting away the
API calls needed to fetch tool definitions and invoke them.

## Available Packages

This repository hosts the following Python packages:

| Package | Key Purpose | Integration | Path | Details (README) | PyPI Status |
| :------ | :---------- | :---------- | :---------------------- | :---------- | :--------- 
| `toolbox-core` | Provides core, framework-agnostic tool handling | Use directly / Custom | `packages/toolbox-core/` | 📄 [View README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-core/README.md) | [![PyPI version](https://badge.fury.io/py/toolbox-core.svg)](https://badge.fury.io/py/toolbox-core) |
| `toolbox-langchain` | Integrates Toolbox tools with the LangChain ecoystem | LangChain / LangGraph | `packages/toolbox-langchain/` | 📄 [View README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-langchain/README.md) | [![PyPI version](https://badge.fury.io/py/toolbox-langchain.svg)](https://badge.fury.io/py/toolbox-langchain) |

## Quickstart

To get started using Toolbox tools with an application, follow these general steps:

1.  **Configure and Run the Toolbox Service:**

    For detailed instructions on setting up and running the Toolbox service
    itself, see: [**Toolbox Getting Started
    Guide**](https://github.com/googleapis/genai-toolbox?tab=readme-ov-file#getting-started)

2.  **Install the Toolbox SDK:**

    Install the appropriate Python SDK package:

    ```bash
    # For the core, framework-agnostic SDK
    pip install toolbox-core

    # OR
    
    # For LangChain/LangGraph integration
    # pip install toolbox-langchain
    ```

3.  **Load Tools Using the SDK Client:**

    Once the service is running and the SDK is installed, use the
    `ToolboxClient` in your Python code to connect to the service and load the
    tools.

    ```py
    from toolbox_core import ToolboxClient
    # from toolbox_langchain import ToolboxClient

    client = ToolboxClient("http://127.0.0.1:5000")

    tools = await client.load_toolset("toolset_name")
    # tools = await client.aload_toolset("toolset_name")
    ```

> [!TIP]
> For a complete, step-by-step walkthrough, please refer to the full tutorial:
> [**Toolbox Quickstart
> Tutorial**](https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart)

## Core Concepts

The following concepts apply generally across the different SDK packages,
although specific method names or object types might vary slightly. Refer to the
individual package READMEs for precise details.

### Connecting to Toolbox

Initialize a client, pointing it to the URL where your Toolbox service is
running.

```py
from toolbox_core import ToolboxClient

# replace with your Toolbox service's URL
client = ToolboxClient("http://127.0.0.1:5000")
```

### Loading Tools

Fetch tool definitions from the Toolbox service. You can load individual tools
by name or load all tools within a specific toolset (or all available toolsets).

```py
# Load a single tool
tool = await client.load_tool("my-tool")

# Load all tools in a specific toolset
tools = await client.load_toolset("my-toolset")

# Load all tools from all toolsets
all_tools = await client.load_toolset()
```

> [!NOTE]
> **Upcoming Feature (`v0.2.0`+):** Support for calling `toolbox.load_toolset()`
> without arguments will be introduced in `v0.2.0`.

### Invoking Tools

Loaded tools behave like callable Python objects or functions.

  * **`toolbox-core`**: Async tools are `awaitable`, sync tools are called
    directly.
  * **`toolbox-langchain`**: Tools conform to LangChain's `BaseTool` interface
    and are typically invoked via `.invoke()` or `.ainvoke()`, often managed by
    a LangGraph agent.

```py
# toolbox-core
result = await tool(param1="value1", param2="value2")

# toolbox-langchain
result = await tool.ainvoke({"param1": "value1", "param2": "value2"})
```

### Synchronous vs. Asynchronous Usage

| Package                 | Loading Tools                                                                                                                                                                                                                            | Invoking Tools                                                                                                                                                                 | Docs                                                                                                              |
| :---------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| **`toolbox-core`** | **Async:**<br/>* **Class:** `ToolboxClient`<br/>* **Methods:** `await client.load_*`<br/><br/>**Sync:**<br/>* **Class:** `ToolboxSyncClient`<br/>* **Methods:** `client.load_*` | **Async:**<br/>* **Class:** `ToolboxTool`<br/>* **Invocation:** `await tool(...)`<br/><br/>**Sync:**<br/>* **Class:** `ToolboxSyncTool`<br/>* **Invocation:** `tool(...)`       | [`toolbox-core` README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-core/README.md#synchronous-usage)                                                     |
| **`toolbox-langchain`** | **Unified Class:** `ToolboxClient`<br/><br/>* **Async Methods:** `await client.aload_*`<br/><br/>* **Sync Methods:** `client.load_*` | **Unified Class:** `ToolboxTool`<br/><br/>* &nbsp;**Async Method:** `await tool.ainvoke()`<br/><br/>* &nbsp;**Sync Method:** `tool.invoke()`                                                   | [`toolbox-langchain` README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-langchain/README.md#asynchronous-usage) |

The `ToolboxSyncClient` handles communication with the Toolbox service *synchronously* and produces `ToolboxSyncTool` instances when you load tools. You do not use the `await` keyword when interacting with these synchronous versions.

```py
from toolbox_core import ToolboxSyncClient

# replace with your Toolbox service's URL
sync_client = ToolboxSyncClient("http://127.0.0.1:5000")

# Load a single tool
tool = sync_client.load_tool("my-tool")

# Load all tools in a specific toolset
tools = sync_client.load_toolset("my-toolset")

# Load all tools from all toolsets
all_tools = sync_client.load_toolset()
```

### Authenticating Tools

Tools configured in the Toolbox service to require authentication need
credentials provided by the SDK during invocation.

#### When is Authentication Needed?

Authentication is configured *per-tool* within the Toolbox service. If a tool
definition specifies it requires authentication (e.g., an "authenticated
parameter"), the SDK must be configured to provide the necessary token.

#### Supported Authentication Mechanisms

Currently, the primary mechanism involves passing **OIDC ID Tokens** (typically
obtained via Google OAuth 2.0) for specific parameters marked as authenticated
in the tool's definition within the Toolbox service. Refer to the [Toolbox
Service Documentation - Authenticated
Parameters](https://googleapis.github.io/genai-toolbox/resources/tools/#authenticated-parameters)
for details on configuring this in the service.

#### SDK Configuration

> [!WARNING]
> Always use HTTPS to connect your application with the Toolbox service,
> especially in production environments or whenever the communication involves
> sensitive data (including scenarios where tools require authentication
> tokens). Using plain HTTP lacks encryption and exposes your application and
> data to significant security risks.

You need to provide the SDK with a function (sync or async) that can retrieve
the required ID token when the tool is called. This function is registered with
the SDK, associating it with the specific authentication requirement defined in
the Toolbox service (matched by name).

```python
from toolbox_core import ToolboxClient

async def get_auth_token():
    # ... Logic to retrieve ID token (e.g., from local storage, OAuth flow)
    # This example just returns a placeholder. Replace with your actual token retrieval.
    return "YOUR_ID_TOKEN" # Placeholder

toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = await toolbox.load_tool("my-tool")

auth_tool = tool.add_auth_token_getters({"my_auth": get_auth_token})

# OR

auth_tool = await toolbox.load_tool("my-tool", auth_token_getters={"my_auth": get_auth_token})

result = auth_tool(input="some input")
```

> [!TIP]
> Your token retriever function is invoked every time an authenticated parameter
> requires a token for a tool call. Consider implementing caching logic within
> this function to avoid redundant token fetching or generation, especially for
> tokens with longer validity periods or if the retrieval process is
> resource-intensive.

### Binding Parameter Values

Pre-set specific parameter values for a tool *before* it's invoked or passed to
an LLM. Bound parameter values are fixed and won't be requested from the LLM.

#### Why Bind Parameters?

  * **Protecting sensitive information:** API keys, secrets, etc.
  * **Enforcing consistency:** Ensuring specific values for certain parameters.
  * **Pre-filling known data:** Pre-fill common or known values.

#### SDK Configuration

> [!IMPORTANT]
> The parameter names used for binding must exactly match the parameter names
> defined in the tool's configuration within the Toolbox service.

> [!NOTE]
> You do not need to modify the tool's configuration in the Toolbox service to
> bind parameter values using the SDK.

Similar to authentication, you can bind parameters after loading a tool or
during the loading process.

```py
from toolbox_core import ToolboxClient

toolbox = ToolboxClient("http://127.0.0.1:5000")
tool = await toolbox.load_tool("my-tool")

bound_tool = tool.bind_parameters({"param": "value"})

# OR

bound_tool = await toolbox.load_tool("my-tool", bound_params={"param": "value"})
```

## Usage Comparison

While the core concepts are similar, the way you integrate and use the tools
varies depending on the chosen SDK package and framework.

| Feature                 | `toolbox-core`                                                                                                   | `toolbox-langchain`                                                                        |
| :---------------------- | :--------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------- |
| **Target Scenario** | Framework-agnostic applications or custom orchestration logic.                                                   | Applications within the LangChain / LangGraph ecosystem.                                   |
| **Client Class(es)** | `ToolboxClient` (async)<br>`ToolboxSyncClient` (sync)                                                             | `ToolboxClient` (provides both sync `load_*` and async `aload_*` methods)                  |
| **Loaded Tool Type** | `ToolboxTool` (async) /<br>`ToolboxSyncTool` (sync)                                                               | `ToolboxTool` instances (compatible with LangChain `BaseTool`)                             |
| **Tool Invocation** | Directly callable / awaitable.                                                                                   | Standard LangChain tool usage patterns.                                                    |
| **LangGraph Integration** | **Requires wrapping:** Tools may need manual wrapping (e.g., `StructuredTool.from_function`) for full LLM use. | **Seamless:** Designed for direct use with `model.bind_tools(tools)` and `ToolNode(tools)`.   |
| **Detailed Examples** | [Core README Section](https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-core#use-with-langgraph)     | [LangChain README Section](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-langchain#use-with-langgraph) |

## Contributing

Contributions are welcome! Please refer to the
[`CONTRIBUTING.md`](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/CONTRIBUTING.md)
to get started.

## License

This project is licensed under the Apache License 2.0. See the
[LICENSE](https://github.com/googleapis/genai-toolbox/blob/main/LICENSE) file
for details.

## Support

If you encounter issues or have questions, please check the existing [GitHub
Issues](https://github.com/googleapis/genai-toolbox/issues) for the main Toolbox
project. If your issue is specific to one of the SDKs, please look for existing
issues [here](https://github.com/googleapis/mcp-toolbox-sdk-python/issues) or
open a new issue in that repository.