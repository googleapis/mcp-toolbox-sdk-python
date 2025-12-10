# Toolbox ADK Integration

This package allows Google ADK agents to natively use tools from the MCP Toolbox.

## Installation

```bash
pip install toolbox-adk
```

## Usage

```python
from toolbox_adk import ToolboxToolset, CredentialStrategy

# Configure auth (e.g., Use the agent's identity)
creds = CredentialStrategy.TOOLBOX_IDENTITY()

# Create the toolset
toolset = ToolboxToolset(
    server_url="http://localhost:5000",
    credentials=creds
)

# Use in your agent
# agent = Agent(tools=toolset.get_tools())
```
