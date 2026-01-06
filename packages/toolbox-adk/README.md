![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)

# Toolbox ADK Integration

This package allows Google ADK (Agent Development Kit) agents to natively use tools from the [MCP Toolbox](https://github.com/googleapis/genai-toolbox).

It provides a seamless bridge between the `toolbox-core` SDK and the ADK's `BaseTool` / `BaseToolset` interfaces, handling authentication propagation, header management, and tool wrapping automatically.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Authentication](#authentication)
    - [Workload Identity (ADC)](#1-workload-identity-adc)
    - [User Identity (OAuth2)](#2-user-identity-oauth2)
    - [API Key](#3-api-key)
    - [HTTP Bearer Token](#4-http-bearer-token)
    - [Manual Google Credentials](#5-manual-google-credentials)
    - [Toolbox Identity (No Auth)](#6-toolbox-identity-no-auth)
    - [Native ADK Integration](#7-native-adk-integration)
    - [Tool-Specific Authentication](#8-tool-specific-authentication)
- [Advanced Configuration](#advanced-configuration)
    - [Additional Headers](#additional-headers)
    - [Global Parameter Binding](#global-parameter-binding)
    - [Usage with Hooks](#usage-with-hooks)

## Installation

```bash
pip install toolbox-adk
```

## Usage

The primary entry point is the `ToolboxToolset`, which loads tools from a remote Toolbox server and adapts them for use with ADK agents.

> [!NOTE]
> The `ToolboxToolset` in this package mirrors the `ToolboxToolset` in the [`adk-python`](https://github.com/google/adk-python) package. The `adk-python` version is a shim that delegates all functionality to this implementation.

```python
from toolbox_adk import ToolboxToolset
from google.adk.agents import Agent

# Create the Toolset
toolset = ToolboxToolset(
    server_url="http://127.0.0.1:5000" 
)

# Use in your ADK Agent
agent = Agent(tools=[toolset])
```

> [!TIP]
> By default, it uses **Toolbox Identity** (no authentication), which is suitable for local development.
>
> For production environments (Cloud Run, GKE) or accessing protected resources, see the [Authentication](#authentication) section for strategies like Workload Identity or OAuth2.

## Authentication

The `ToolboxToolset` requires credentials to authenticate with the Toolbox server. You can configure these credentials using the `CredentialStrategy` factory methods.

The strategies handle two main types of authentication:
*   **Client-to-Server**: Securing the connection to the Toolbox server (e.g., Workload Identity, API keys).
*   **User Identity**: Authenticating the end-user for specific tools (e.g., 3-legged OAuth).

### 1. Workload Identity (ADC)
*Recommended for Cloud Run, GKE, or local development with `gcloud auth login`.*

Uses the agent's Application Default Credentials (ADC) to generate an OIDC token. This is the standard way for one service to authenticate to another on Google Cloud.

```python
from toolbox_adk import CredentialStrategy, ToolboxToolset

# target_audience: The URL of your Toolbox server
creds = CredentialStrategy.workload_identity(target_audience="https://my-toolbox-service.run.app")

toolset = ToolboxToolset(
    server_url="https://my-toolbox-service.run.app",
    credentials=creds
)
```

### 2. User Identity (OAuth2)
*Recommended for tools that act on behalf of the user.*

Configures the ADK-native interactive 3-legged OAuth flow to get consent and credentials from the end-user at runtime. This strategy is passed to the `ToolboxToolset` just like any other credential strategy.

```python
from toolbox_adk import CredentialStrategy, ToolboxToolset

creds = CredentialStrategy.user_identity(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# The toolset will now initiate OAuth flows when required by tools
toolset = ToolboxToolset(
    server_url="...",
    credentials=creds
)
```

### 3. API Key
*Use a static API key passed in a specific header (default: `X-API-Key`).*

```python
from toolbox_adk import CredentialStrategy

# Default header: X-API-Key
creds = CredentialStrategy.api_key(key="my-secret-key")

# Custom header
creds = CredentialStrategy.api_key(key="my-secret-key", header_name="X-My-Header")
```

### 4. HTTP Bearer Token
*Manually supply a static bearer token.*

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.manual_token(token="your-static-bearer-token")
```

### 5. Manual Google Credentials
*Use an existing `google.auth.credentials.Credentials` object.*

```python
from toolbox_adk import CredentialStrategy
import google.auth

creds_obj, _ = google.auth.default()
creds = CredentialStrategy.manual_credentials(credentials=creds_obj)
```

### 6. Toolbox Identity (No Auth)
*Use this if your Toolbox server does not require authentication (e.g., local development).*

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.toolbox_identity()
```

### 7. Native ADK Integration
*Convert ADK-native `AuthConfig` or `AuthCredential` objects.*

```python
from toolbox_adk import CredentialStrategy

# From AuthConfig
creds = CredentialStrategy.from_adk_auth_config(auth_config)

# From AuthCredential + AuthScheme
creds = CredentialStrategy.from_adk_credentials(auth_credential, scheme)
```

### 8. Tool-Specific Authentication
*Resolve authentication tokens dynamically for specific tools.*

Some tools may define their own authentication requirements (e.g., Salesforce OAuth, GitHub PAT) via `authSources` in their schema. You can provide a mapping of getters to resolve these tokens at runtime.

```python
async def get_salesforce_token():
    # Fetch token from secret manager or reliable source
    return "sf-access-token"

toolset = ToolboxToolset(
    server_url="...",
    auth_token_getters={
        "salesforce-auth": get_salesforce_token,   # Async callable
        "github-pat": lambda: "my-pat-token"       # Sync callable or static lambda
    }
)
```

## Advanced Configuration

### Additional Headers

You can inject custom headers into every request made to the Toolbox server. This is useful for passing tracing IDs, API keys, or other metadata.

```python
toolset = ToolboxToolset(
    server_url="...",
    additional_headers={
        "X-Trace-ID": "12345",
        "X-My-Header": lambda: get_dynamic_header_value() # Can be a callable
    }
)
```

### Global Parameter Binding

Bind values to tool parameters globally across all loaded tools. These values will be **fixed** and **hidden** from the LLM.

*   **Schema Hiding**: The bound parameters are removed from the tool schema sent to the model, simplifying the context window.
*   **Auto-Injection**: The values are automatically injected into the tool arguments during execution.

```python
toolset = ToolboxToolset(
    server_url="...",
    bound_params={
        # 'region' will be removed from the LLM schema and injected automatically
        "region": "us-central1",
        "api_key": lambda: get_api_key() # Can be a callable
    }
)
```

### Usage with Hooks

You can attach `pre_hook` and `post_hook` functions to execute logic before and after every tool invocation.

> [!NOTE]
> The `pre_hook` can modify `context.arguments` to dynamically alter the inputs passed to the tool.

```python
from toolbox_adk import ToolboxContext

async def log_start(context: ToolboxContext):
    print(f"Starting tool with args: {context.arguments}")
    # context.tool_context is the underlying ADK ToolContext
    # Example: Inject or modify arguments
    # context.arguments["user_id"] = "123"

async def log_end(context: ToolboxContext):
    print("Finished tool execution")
    # Inspect result or error
    if context.error:
        print(f"Tool failed: {context.error}")
    else:
        print(f"Tool succeeded with result: {context.result}")

toolset = ToolboxToolset(
    server_url="...",
    pre_hook=log_start,
    post_hook=log_end
)
```

## Contributing

Contributions are welcome! Please refer to the `toolbox-core` [DEVELOPER.md](../toolbox-core/DEVELOPER.md) for general guidelines.

## License

This project is licensed under the Apache License 2.0.
