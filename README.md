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
- [Which Package Should I Use?](#which-package-should-i-use)
- [Available Packages](#available-packages)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

<!-- /TOC -->

## Overview

The MCP Toolbox service provides a centralized way to manage and expose tools
(like API connectors, database query tools, etc.) for use by GenAI applications.

These Python SDKs act as clients for that service. They handle the communication needed to:

* Fetch tool definitions from your running Toolbox instance.
* Provide convenient Python objects or functions representing those tools.
* Invoke the tools (calling the underlying APIs/services configured in Toolbox).
* Handle authentication and parameter binding as needed.

By using these SDKs, you can easily leverage your Toolbox-managed tools directly
within your Python applications or AI orchestration frameworks.

## Which Package Should I Use?

Choosing the right package depends on how you are building your application:

* [`toolbox-langchain`](https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-langchain):
  Use this package if you are building your application using the LangChain or
  LangGraph frameworks. It provides tools that are directly compatible with the
  LangChain ecosystem (`BaseTool` interface), simplifying integration.
* [`toolbox-llamaindex`](https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-llamaindex):
  Use this package if you are building your application using the LlamaIndex framework. 
  It provides tools that are directly compatible with the
  LlamaIndex ecosystem (`BaseTool` interface), simplifying integration.
* [`toolbox-core`](https://github.com/googleapis/mcp-toolbox-sdk-python/tree/main/packages/toolbox-core):
  Use this package if you are not using LangChain/LangGraph or any other
  orchestration framework, or if you need a framework-agnostic way to interact
  with Toolbox tools (e.g., for custom orchestration logic or direct use in
  Python scripts).

## Available Packages

This repository hosts the following Python packages. See the package-specific
README for detailed installation and usage instructions:

| Package | Target Use Case | Integration | Path | Details (README) | PyPI Status |
| :------ | :---------- | :---------- | :---------------------- | :---------- | :--------- 
| `toolbox-core` | Framework-agnostic / Custom applications | Use directly / Custom | `packages/toolbox-core/` | 📄 [View README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-core/README.md) | [![PyPI version](https://badge.fury.io/py/toolbox-core.svg)](https://badge.fury.io/py/toolbox-core.svg) |
| `toolbox-langchain` | LangChain / LangGraph applications | LangChain / LangGraph | `packages/toolbox-langchain/` | 📄 [View README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-langchain/README.md) | [![PyPI version](https://badge.fury.io/py/toolbox-langchain.svg)](https://badge.fury.io/py/toolbox-langchain.svg) |
| `toolbox-llamaindex` | LlamaIndex  applications                 | LlamaIndex            | `packages/toolbox-llamaindex/` | 📄 [View README](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-llamaindex/README.md) | [![PyPI version](https://badge.fury.io/py/toolbox-llamaindex.svg)](https://badge.fury.io/py/toolbox-llamaindex.svg) |

## Getting Started

To get started using Toolbox tools with an application, follow these general steps:

1.  **Set up and Run the Toolbox Service:**

    Before using the SDKs, you need the main MCP Toolbox service running. Follow
    the instructions here: [**Toolbox Getting Started
    Guide**](https://github.com/googleapis/genai-toolbox?tab=readme-ov-file#getting-started)

2.  **Install the Appropriate SDK:**
    
    Choose the package based on your needs (see "[Which Package Should I Use?](#which-package-should-i-use)" above) and install it:

    ```bash
    # For the core, framework-agnostic SDK
    pip install toolbox-core

    # OR

    # For LangChain/LangGraph integration
    pip install toolbox-langchain
    
    # For the LlamaIndex integration
    pip install toolbox-llamaindex
    ```

3.  **Use the SDK:**

    Consult the README for your chosen package (linked in the "[Available
    Packages](#available-packages)" section above) for detailed instructions on
    how to connect the client, load tool definitions, invoke tools, configure
    authentication/binding, and integrate them into your application or
    framework.

> [!TIP]
> For a complete, end-to-end example including setting up the service and using
> an SDK, see the full tutorial: [**Toolbox Quickstart
> Tutorial**](https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart)

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
open a new issue in this repository.
