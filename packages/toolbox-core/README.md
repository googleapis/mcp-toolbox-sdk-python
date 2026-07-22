![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/mcp-toolbox/main/logo.png)

# MCP Toolbox Core SDK

[![PyPI version](https://badge.fury.io/py/toolbox-core.svg)](https://badge.fury.io/py/toolbox-core) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/toolbox-core)](https://pypi.org/project/toolbox-core/) [![Coverage Status](https://coveralls.io/repos/github/googleapis/mcp-toolbox/badge.svg?branch=main)](https://coveralls.io/github/googleapis/mcp-toolbox?branch=main)
 [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This SDK allows you to seamlessly integrate the functionalities of
[MCP Toolbox](https://github.com/googleapis/mcp-toolbox) allowing you to load and
use tools defined in the service as standard Python functions within your GenAI
applications.

For detailed guides, authentication examples, and advanced configuration, visit the [Python SDK Core Guide](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/).

<!-- TOC ignore:true -->
<!-- TOC -->

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

<!-- /TOC -->

## Installation

```bash
pip install toolbox-core
```

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

## Usage

The core package provides a framework-agnostic way to interact with your Toolbox server. For detailed guides and advanced configuration, please visit the following sections on our [Documentation Site](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/):

- [Transport Protocols](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#transport-protocols)
- [Loading Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#loading-tools)
- [Invoking Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#invoking-tools)
- [Synchronous Usage](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#synchronous-usage)
- [Use With Langraph](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#use-with-langgraph)
- [Client to Server Authentication](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#client-to-server-authentication)
- [Authenticating Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#authenticating-tools)
- [Binding Parameter Values](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#parameter-binding)
- [OpenTelemetry](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/core/#opentelemetry)


# Contributing

Contributions are welcome! Please refer to the [`DEVELOPER.md`](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-core/DEVELOPER.md) file for guidelines on how to set up a development environment and run tests.

# License

This project is licensed under the Apache License 2.0. See the
[LICENSE](https://github.com/googleapis/mcp-toolbox/blob/main/LICENSE) file for details.

# Support

If you encounter issues or have questions, check the existing [GitHub Issues](https://github.com/googleapis/mcp-toolbox/issues) for the main Toolbox project.
