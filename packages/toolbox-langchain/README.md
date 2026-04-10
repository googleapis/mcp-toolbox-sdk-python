![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)
# MCP Toolbox LangChain SDK

This SDK allows you to seamlessly integrate the functionalities of
[MCP Toolbox](https://github.com/googleapis/genai-toolbox) into your LangChain GenAI
applications, enabling advanced orchestration and interaction with LLMs.

For detailed guides, authentication examples, and advanced configuration, visit the [Python SDK Langchain Guide](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/).

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
pip install toolbox-langchain
```

## Quickstart

Here's a minimal example to get you started using
[LangGraph](https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.chat_agent_executor.create_react_agent):

```py
from toolbox_langchain import ToolboxClient
from langchain_google_vertexai import ChatVertexAI
from langgraph.prebuilt import create_react_agent

async with ToolboxClient("http://127.0.0.1:5000") as toolbox:
    tools = toolbox.load_toolset()

    model = ChatVertexAI(model="gemini-3-flash-preview")
    agent = create_react_agent(model, tools)

    prompt = "How's the weather today?"

    for s in agent.stream({"messages": [("user", prompt)]}, stream_mode="values"):
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()
```

## Usage

The toolbox-langchain package provids a dedicated integration to seamlessly load and use MCP Toolbox tools within the LangChain orchestration framework. For detailed guides and advanced configuration, please visit the following sections on our [Documentation Site](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/):

- [Transport Protocols](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#transport-protocols)
- [Loading Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#loading-tools)
- [Use with Langchain](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#use-with-langchain)
- [Use with Langraph](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#use-with-langgraph)
- [Manual Usage](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#manual-usage)
- [Client to Server Authentication](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#client-to-server-authentication)
- [Authenticating Tools](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#authenticating-tools)
- [Binding Parameter Values](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#parameter-binding)
- [Asynchronous Usage](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#asynchronous-usage)
- [OpenTelemetry](https://mcp-toolbox.dev/documentation/connect-to/toolbox-sdks/python-sdk/langchain/#opentelemetry)

# Contributing

Contributions are welcome! Please refer to the [`DEVELOPER.md`](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/packages/toolbox-langchain/DEVELOPER.md) file for guidelines on how to set up a development environment and run tests.

# License

This project is licensed under the Apache License 2.0. See the
[LICENSE](https://github.com/googleapis/genai-toolbox/blob/main/LICENSE) file for details.

# Support

If you encounter issues or have questions, check the existing [GitHub Issues](https://github.com/googleapis/genai-toolbox/issues) for the main Toolbox project.