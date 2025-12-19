![MCP Toolbox Logo](https://raw.githubusercontent.com/googleapis/genai-toolbox/main/logo.png)

# Toolbox ADK Integration

This package allows Google ADK (Agent Development Kit) agents to natively use tools from the [MCP Toolbox](https://github.com/googleapis/genai-toolbox).

It provides a seamless bridge between the `toolbox-core` SDK and the ADK's `BaseTool` / `BaseToolset` interfaces, handling authentication propagation, header management, and tool wrapping automatically.

## Installation

```bash
pip install toolbox-adk
```

## Usage

The primary entry point is the `ToolboxToolset`, which loads tools from a remote Toolbox server and adapts them for use with ADK agents.

> [!NOTE]
> The `ToolboxToolset` in this package mirrors the `ToolboxToolset` in the [`adk-python`](https://github.com/google/adk-python) package. The `adk-python` version is a shim that delegates all functionality to this implementation.

This section describes how to configure and use the `ToolboxToolset`.

### Authentication

The `ToolboxToolset` requires credentials to authenticate with the Toolbox server. You can configure these credentials using the `CredentialStrategy` class.

#### Supported Strategies

##### 1. Toolbox Identity
Use the agent's identity to authenticate with the Toolbox server. This is typically used when the agent itself has been granted permissions within the Toolbox system.

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.toolbox_identity()
```

##### 2. User Identity (OAuth2)
Configures the ADK-native interactive 3-legged OAuth flow to get consent and credentials from the end-user at runtime.

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.user_identity(
    client_id="your-client-id",
    client_secret="your-client-secret",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
```

##### 3. Workload Identity (ADC)
Uses the agent's Application Default Credentials (ADC). Suitable for Cloud Run, GKE, or local development with `gcloud auth login`.

```python
from toolbox_adk import CredentialStrategy

# target_audience: The audience for the generated ID token
creds = CredentialStrategy.workload_identity(target_audience="https://my-service-url")
```

##### 4. HTTP Bearer Token
Use a static bearer token for authentication.

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.manual_token(token="your-static-bearer-token")
```

##### 5. Manual Google Credentials
Use an existing `google.auth.credentials.Credentials` object.

```python
from toolbox_adk import CredentialStrategy
import google.auth

creds_obj, _ = google.auth.default()
creds = CredentialStrategy.manual_credentials(credentials=creds_obj)
```

##### 6. API Key
Use a static API key passed in a specific header (default: `X-API-Key`).

```python
from toolbox_adk import CredentialStrategy

# Default header: X-API-Key
creds = CredentialStrategy.api_key(key="my-secret-key")

# Custom header
creds = CredentialStrategy.api_key(key="my-secret-key", header_name="X-My-Header")
```

##### 7. Authentication from ADK
If you are using the ADK `Tool` class, you can automatically convert ADK credentials to Toolbox credentials.
This supports **OAuth2**, **HTTP Bearer**, and **API Key**.

```python
from toolbox_adk import CredentialStrategy

# auth_scheme: The ADK AuthScheme definition
# auth_credential: The runtime credential collected by ADK
toolbox_creds = CredentialStrategy.from_adk_credentials(auth_scheme, auth_credential)
```

### Creating the Toolset

Once you have configured your credentials, you can create an instance of `ToolboxToolset`.

```python
from toolbox_adk import ToolboxToolset, CredentialStrategy
from google.adk.agents import Agent

# 1. Configure Authentication Strategy
# Use the agent's own identity (Workload Identity)
creds = CredentialStrategy.workload_identity(target_audience="https://my-toolbox-service-url")

# 2. Create the Toolset
toolset = ToolboxToolset(
    server_url="https://my-toolbox-service-url",
    toolset_name="my-toolset", # Optional: Load specific toolset
    credentials=creds
)

# 3. Use in your ADK Agent
agent = Agent(tools=[toolset])
```

## Authentication Strategies

The `toolbox-adk` package provides flexible authentication strategies to handle `Client-to-Server` authentication (securing the connection to the Toolbox server) and `User Identity` propagation (authenticating the user for specific tools).

Use the `CredentialStrategy` factory methods to create your configuration.

### Workload Identity (Recommended for Cloud Run / GKE)

Uses the agent's environment credentials (ADC) to generate an OIDC ID token. This is the standard way for one service to authenticate to another on Google Cloud.

```python
# target_audience should match the URL of your Toolbox server
creds = CredentialStrategy.workload_identity(target_audience="https://my-toolbox-service.run.app")

toolset = ToolboxToolset(
    server_url="https://my-toolbox-service.run.app",
    credentials=creds
)
```

### User Identity (3-Legged OAuth)

Propagates the end-user's identity to the Toolbox. This is used when the tools themselves need to act on behalf of the user (e.g., accessing the user's Drive or Calendar).

```python
creds = CredentialStrategy.user_identity(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    scopes=["https://www.googleapis.com/auth/drive"]
)
```

### Manual Token (Development / Testing)

Manually supply a token (e.g., a static API key or a temporary token).

```python
creds = CredentialStrategy.manual_token(token="my-secret-token")
```

### Manual Credentials Object

Uses a provided `google.auth` Credentials object directly.

```python
from google.oauth2 import service_account

my_creds = service_account.Credentials.from_service_account_file('key.json')
creds = CredentialStrategy.manual_credentials(my_creds)
```

### API Key

Use a static API key passed in a specific header (default: `X-API-Key`).

```python
# Default header: X-API-Key
creds = CredentialStrategy.api_key(key="my-secret-key")

# Custom header
creds = CredentialStrategy.api_key(key="my-secret-key", header_name="X-My-Header")
```

### Toolbox Identity (No Auth)

Use this if your Toolbox server does not require authentication (e.g., local development).

```python
creds = CredentialStrategy.toolbox_identity()
```

### Native ADK Integration

If you are using ADK's configuration system (`AuthConfig` objects), you can create the strategy directly from it.

```python
# auth_config is an instance of google.adk.auth.auth_tool.AuthConfig
creds = CredentialStrategy.from_adk_auth_config(auth_config)
```

Or if you have the `AuthScheme` and `AuthCredential` objects separately:

```python
# scheme is google.adk.auth.auth_tool.AuthScheme
# credential is google.adk.auth.auth_credential.AuthCredential
creds = CredentialStrategy.from_adk_credentials(auth_credential, scheme)
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

Bind values to tool parameters globally across all loaded tools. These values will be fixed and hidden from the LLM.

```python
toolset = ToolboxToolset(
    server_url="...",
    bound_params={
        "region": "us-central1",
        "api_key": lambda: get_api_key() # Can be a callable
    }
)
```

### Auth Token Getters

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
