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

For comprehensive guides and advanced configuration, visit the [Main Documentation Site](https://googleapis.github.io/genai-toolbox/).


<!-- TOC -->
- [Available Packages](#available-packages)
- [Quickstart](#quickstart)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

<!-- /TOC -->

## Available Packages

This repository hosts the following Python packages. See the package-specific READMEs or the docsite for detailed usage:

| Package | Target Use Case | Path | Documentation |
| :------ | :---------- | :--- | :---------- |
| `toolbox-core` | Framework-agnostic / Custom apps | `packages/toolbox-core/` | [Python Core Guide](https://googleapis.github.io/genai-toolbox/sdks/python-sdk/core/) |
| `toolbox-adk` | Google ADK Integration | `packages/toolbox-adk/` | [ADK Package Guide](https://googleapis.github.io/genai-toolbox/sdks/python-sdk/adk/) |
| `toolbox-langchain` | LangChain / LangGraph Integration | `packages/toolbox-langchain/` | [LangChain Guide](https://googleapis.github.io/genai-toolbox/sdks/python-sdk/langchain/) |
| `toolbox-llamaindex` | LlamaIndex Integration | `packages/toolbox-llamaindex/` | [LlamaIndex Guide](https://googleapis.github.io/genai-toolbox/sdks/python-sdk/llamaindex/) |

## Quickstart

1.  **Set up the Toolbox Service**: Ensure you have a running MCP Toolbox server. Follow the [MCP Toolbox Server Getting Started Guide](https://github.com/googleapis/genai-toolbox?tab=readme-ov-file#getting-started).
2.  **Install the Appropriate SDK:**

    ```bash
    # For the Google ADK
    pip install toolbox-adk

    # OR
    
    # For the core, framework-agnostic SDK
    pip install toolbox-core

    # OR

    # For LangChain/LangGraph integration
    pip install toolbox-langchain

    # OR
    
    # For the LlamaIndex integration
    pip install toolbox-llamaindex

3.  **Explore Tutorials**: Check out the [Python Quickstart Tutorial](https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart/) for a full walkthrough.

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
