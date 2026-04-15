![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/mcp-toolbox/main/logo.png)
# MCP Toolbox LlamaIndex SDK

This SDK allows you to seamlessly integrate the functionalities of
[MCP Toolbox](https://github.com/googleapis/mcp-toolbox) into your LlamaIndex LLM
applications, enabling advanced orchestration and interaction with GenAI models.

For detailed guides, authentication examples, and advanced configuration, visit the [Python SDK LlamaIndex Guide](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/).

<!-- TOC ignore:true -->
## Table of Contents
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
  async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
    tools = toolbox.load_toolset()

    vertex_model = GoogleGenAI(
        model="gemini-3-flash-preview",
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

The `toolbox-llamaindex` package provides a dedicated integration to seamlessly load and use MCP Toolbox tools within the LlamaIndex orchestration framework. For detailed guides and advanced configuration, please visit the following sections on our [Documentation Site](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/):


- [Transport Protocols](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#transport-protocols)
- [Loading Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#loading-tools)
- [Use with LlamaIndex](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#use-with-llamaindex)
- [Manual Usage](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#manual-usage)
- [Client to Server Authentication](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#client-to-server-authentication)
- [Authenticating Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#authenticating-tools)
- [Binding Parameter Values](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#parameter-binding)
- [Asynchronous Usage](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#asynchronous-usage)
- [OpenTelemetry](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/llamaindex/#opentelemetry)

# Contributing 

Contributions are welcome! Please refer to the [`DEVELOPER.md`](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-llamaindex/DEVELOPER.md) file for guidelines on how to set up a development environment and run tests.

# License

This project is licensed under the Apache License 2.0. See the
[LICENSE](https://github.com/googleapis/mcp-toolbox/blob/main/LICENSE) file for details.

# Support

If you encounter issues or have questions, check the existing [GitHub Issues](https://github.com/googleapis/mcp-toolbox/issues) for the main Toolbox project.