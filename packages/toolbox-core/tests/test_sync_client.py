# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import inspect
from typing import Any, Callable, Mapping, Optional
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import CallbackResult, aioresponses

from toolbox_core.client import ToolboxClient
from toolbox_core.protocol import ManifestSchema, ParameterSchema, ToolSchema
from toolbox_core.sync_client import ToolboxSyncClient
from toolbox_core.sync_tool import ToolboxSyncTool

TEST_BASE_URL = "http://toolbox.example.com"


@pytest.fixture(autouse=True)
def manage_sync_client_class_state():
    """
    Resets the class-level event loop and thread for ToolboxSyncClient
    before and after each test to ensure test isolation.
    """
    # Save current state if any
    original_loop = getattr(ToolboxSyncClient, "_ToolboxSyncClient__loop", None)
    original_thread = getattr(ToolboxSyncClient, "_ToolboxSyncClient__thread", None)

    # Reset for the test
    ToolboxSyncClient._ToolboxSyncClient__loop = None
    ToolboxSyncClient._ToolboxSyncClient__thread = None

    yield  # Run the test

    # Teardown: stop the loop and join the thread created during the test (if any)
    # This ensures that each test (or the first client in it) starts fresh
    test_loop = getattr(ToolboxSyncClient, "_ToolboxSyncClient__loop", None)
    test_thread = getattr(ToolboxSyncClient, "_ToolboxSyncClient__thread", None)

    if test_loop and test_loop.is_running():
        test_loop.call_soon_threadsafe(test_loop.stop)
    if test_thread and test_thread.is_alive():
        # Wait for the run_forever loop to exit after stop()
        test_thread.join(timeout=2)

    # Restore original state (likely None if tests are isolated, but good practice)
    ToolboxSyncClient._ToolboxSyncClient__loop = original_loop
    ToolboxSyncClient._ToolboxSyncClient__thread = original_thread


@pytest.fixture()
def test_tool_str_schema():
    return ToolSchema(
        description="Test Tool with String input",
        parameters=[
            ParameterSchema(
                name="param1", type="string", description="Description of Param1"
            )
        ],
    )


@pytest.fixture()
def test_tool_int_bool_schema():
    return ToolSchema(
        description="Test Tool with Int, Bool",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(name="argB", type="boolean", description="Argument B"),
        ],
    )


@pytest.fixture()
def test_tool_auth_schema():
    return ToolSchema(
        description="Test Tool with Int,Bool+Auth",
        parameters=[
            ParameterSchema(name="argA", type="integer", description="Argument A"),
            ParameterSchema(
                name="argB",
                type="boolean",
                description="Argument B",
                authSources=["my-auth-service"],
            ),
        ],
    )


@pytest.fixture
def tool_schema_minimal():
    return ToolSchema(description="Minimal Test Tool", parameters=[])


# --- Helper Functions for Mocking ---
def mock_tool_load(
    aio_resp: aioresponses,
    tool_name: str,
    tool_schema: ToolSchema,
    base_url: str = TEST_BASE_URL,
    server_version: str = "0.0.0",
    status: int = 200,
    callback: Optional[Callable] = None,
    payload_override: Optional[Any] = None,
):
    url = f"{base_url}/api/tool/{tool_name}"
    payload_data = {}
    if payload_override is not None:
        payload_data = payload_override
    else:
        manifest = ManifestSchema(
            serverVersion=server_version, tools={tool_name: tool_schema}
        )
        payload_data = manifest.model_dump()
    aio_resp.get(url, payload=payload_data, status=status, callback=callback)


def mock_toolset_load(
    aio_resp: aioresponses,
    toolset_name: str,
    tools_dict: Mapping[str, ToolSchema],
    base_url: str = TEST_BASE_URL,
    server_version: str = "0.0.0",
    status: int = 200,
    callback: Optional[Callable] = None,
):
    url_path = f"toolset/{toolset_name}" if toolset_name else "toolset/"
    url = f"{base_url}/api/{url_path}"
    manifest = ManifestSchema(serverVersion=server_version, tools=tools_dict)
    aio_resp.get(url, payload=manifest.model_dump(), status=status, callback=callback)


def mock_tool_invoke(
    aio_resp: aioresponses,
    tool_name: str,
    base_url: str = TEST_BASE_URL,
    response_payload: Any = {"result": "ok"},
    status: int = 200,
    callback: Optional[Callable] = None,
):
    url = f"{base_url}/api/tool/{tool_name}/invoke"
    aio_resp.post(url, payload=response_payload, status=status, callback=callback)


# --- Tests for ToolboxSyncClient ---


def test_sync_client_initialization_and_loop_management():
    """Tests that the event loop and thread are managed correctly at class level."""
    client1 = ToolboxSyncClient(TEST_BASE_URL)
    assert client1._ToolboxSyncClient__loop is not None, "Loop should be created"
    assert client1._ToolboxSyncClient__thread is not None, "Thread should be created"
    assert client1._ToolboxSyncClient__thread.is_alive(), "Thread should be running"
    assert isinstance(
        client1._ToolboxSyncClient__async_client, ToolboxClient
    ), "Async client should be ToolboxClient instance"

    loop1 = client1._ToolboxSyncClient__loop
    thread1 = client1._ToolboxSyncClient__thread

    client2 = ToolboxSyncClient(TEST_BASE_URL)  # Should reuse existing loop/thread
    assert client2._ToolboxSyncClient__loop is loop1, "Loop should be reused"
    assert client2._ToolboxSyncClient__thread is thread1, "Thread should be reused"
    assert isinstance(client2._ToolboxSyncClient__async_client, ToolboxClient)

    client1.close()  # Closes its async_client's session
    client2.close()  # Closes its async_client's session
    # Loop/thread are stopped by the manage_sync_client_class_state fixture


def test_sync_client_close_method():
    """Tests the close() method of ToolboxSyncClient."""
    mock_async_client_instance = AsyncMock(spec=ToolboxClient)
    mock_async_client_instance.close = AsyncMock(
        return_value=None
    )  # close() is a coroutine

    with patch(
        "toolbox_core.sync_client.ToolboxClient",
        return_value=mock_async_client_instance,
    ) as MockedAsyncClientConst:
        client = ToolboxSyncClient(TEST_BASE_URL)
        # Ensure the constructor was called
        MockedAsyncClientConst.assert_called_once_with(
            TEST_BASE_URL, client_headers=None
        )

        client.close()
        mock_async_client_instance.close.assert_awaited_once()


def test_sync_client_context_manager(aioresponses, tool_schema_minimal):
    """Tests the context manager (__enter__ and __exit__) functionality."""
    with patch.object(
        ToolboxSyncClient, "close", wraps=ToolboxSyncClient.close, autospec=True
    ) as mock_close_method:
        with ToolboxSyncClient(TEST_BASE_URL) as client:
            assert isinstance(client, ToolboxSyncClient)
            # Perform some action that would use the client if needed
            mock_tool_load(aioresponses, "dummy_tool_ctx", tool_schema_minimal)
            client.load_tool("dummy_tool_ctx")
        mock_close_method.assert_called_once()

    # Test __exit__ calls close even with an exception
    with patch.object(
        ToolboxSyncClient, "close", wraps=ToolboxSyncClient.close, autospec=True
    ) as mock_close_method_exc:
        with pytest.raises(ValueError, match="Test exception"):
            with ToolboxSyncClient(TEST_BASE_URL) as client_exc:
                raise ValueError("Test exception")
        mock_close_method_exc.assert_called_once()


def test_sync_load_tool_success(aioresponses, test_tool_str_schema):
    TOOL_NAME = "test_tool_sync_1"
    mock_tool_load(aioresponses, TOOL_NAME, test_tool_str_schema)
    mock_tool_invoke(
        aioresponses, TOOL_NAME, response_payload={"result": "sync_tool_ok"}
    )

    with ToolboxSyncClient(TEST_BASE_URL) as client:
        loaded_tool = client.load_tool(TOOL_NAME)

        assert callable(loaded_tool)
        assert isinstance(loaded_tool, ToolboxSyncTool)
        assert loaded_tool.__name__ == TOOL_NAME

        # Check __doc__ and __signature__ (assuming ToolboxSyncTool delegates these)
        # The underlying async ToolboxTool generates these.
        expected_description = (
            test_tool_str_schema.description
            + f"\n\nArgs:\n    param1 (str): Description of Param1"  # This format comes from ToolboxTool
        )
        assert test_tool_str_schema.description in loaded_tool.__doc__

        sig = inspect.signature(loaded_tool)
        assert list(sig.parameters.keys()) == [
            p.name for p in test_tool_str_schema.parameters
        ]

        result = loaded_tool(param1="some value")
        assert result == "sync_tool_ok"


def test_sync_load_toolset_success(
    aioresponses, test_tool_str_schema, test_tool_int_bool_schema
):
    TOOLSET_NAME = "my_sync_toolset"
    TOOL1_NAME = "sync_tool1"
    TOOL2_NAME = "sync_tool2"

    tools_definition = {
        TOOL1_NAME: test_tool_str_schema,
        TOOL2_NAME: test_tool_int_bool_schema,
    }
    mock_toolset_load(aioresponses, TOOLSET_NAME, tools_definition)

    # Mock invocations for each tool if we were to call them
    mock_tool_invoke(
        aioresponses, TOOL1_NAME, response_payload={"result": f"{TOOL1_NAME}_ok"}
    )
    mock_tool_invoke(
        aioresponses, TOOL2_NAME, response_payload={"result": f"{TOOL2_NAME}_ok"}
    )

    with ToolboxSyncClient(TEST_BASE_URL) as client:
        tools = client.load_toolset(TOOLSET_NAME)

        assert isinstance(tools, list)
        assert len(tools) == len(tools_definition)
        assert all(isinstance(t, ToolboxSyncTool) for t in tools)
        assert {t.__name__ for t in tools} == tools_definition.keys()

        # Optionally, invoke one of the tools
        tool1 = next(t for t in tools if t.__name__ == TOOL1_NAME)
        result1 = tool1(param1="hello")
        assert result1 == f"{TOOL1_NAME}_ok"


def test_sync_invoke_tool_server_error(aioresponses, test_tool_str_schema):
    TOOL_NAME = "sync_server_error_tool"
    ERROR_MESSAGE = "Simulated Server Error for Sync Client"

    mock_tool_load(aioresponses, TOOL_NAME, test_tool_str_schema)
    mock_tool_invoke(
        aioresponses, TOOL_NAME, response_payload={"error": ERROR_MESSAGE}, status=500
    )

    with ToolboxSyncClient(TEST_BASE_URL) as client:
        loaded_tool = client.load_tool(TOOL_NAME)
        with pytest.raises(Exception, match=ERROR_MESSAGE):
            loaded_tool(param1="some input")  # Synchronous call


def test_sync_load_tool_not_found_in_manifest(aioresponses, test_tool_str_schema):
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_sync_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_sync_xyz"

    # Server returns a manifest, but it doesn't contain REQUESTED_TOOL_NAME
    mismatched_manifest_payload = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str_schema}
    ).model_dump()

    mock_tool_load(
        aio_resp=aioresponses,
        tool_name=REQUESTED_TOOL_NAME,  # URL that will be called
        tool_schema=test_tool_str_schema,  # Dummy schema for mock_tool_load structure
        payload_override=mismatched_manifest_payload,  # Actual payload returned
    )

    with ToolboxSyncClient(TEST_BASE_URL) as client:
        # The error comes from the underlying async client's parsing
        with pytest.raises(
            ValueError,
            match=f"Tool '{REQUESTED_TOOL_NAME}' not found!",
        ):
            client.load_tool(REQUESTED_TOOL_NAME)

    aioresponses.assert_called_once_with(
        f"{TEST_BASE_URL}/api/tool/{REQUESTED_TOOL_NAME}", method="GET", headers={}
    )


def test_sync_add_headers_success(aioresponses, test_tool_str_schema):
    """Tests adding headers after client initialization for sync client."""
    tool_name = "tool_after_add_headers_sync"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={tool_name: test_tool_str_schema}
    )
    expected_payload = {"result": "added_sync_ok"}
    headers_to_add = {"X-Custom-SyncHeader": "sync_value"}

    # Mock GET for tool load - should include new headers
    def get_callback(url, **kwargs):
        assert kwargs.get("headers") == headers_to_add
        return CallbackResult(status=200, payload=manifest.model_dump())

    aioresponses.get(f"{TEST_BASE_URL}/api/tool/{tool_name}", callback=get_callback)

    # Mock POST for tool invoke - should include new headers
    def post_callback(url, **kwargs):
        assert kwargs.get("headers") == headers_to_add
        return CallbackResult(status=200, payload=expected_payload)

    aioresponses.post(
        f"{TEST_BASE_URL}/api/tool/{tool_name}/invoke", callback=post_callback
    )

    with ToolboxSyncClient(TEST_BASE_URL) as client:
        client.add_headers(headers_to_add)
        # Verification of header addition is via the callbacks in aioresponses

        tool = client.load_tool(tool_name)
        result = tool(param1="test")
        assert result == expected_payload["result"]


def test_sync_add_headers_duplicate_fail(aioresponses):
    """Tests that adding a duplicate header via add_headers raises ValueError (from async client)."""
    initial_headers = {"X-Initial-Header": "initial_value"}
    mock_async_client = AsyncMock(spec=ToolboxClient)

    # Configure add_headers to simulate the ValueError from ToolboxClient
    async def mock_add_headers_async(headers):
        # Simulate ToolboxClient's check
        if "X-Initial-Header" in headers:
            raise ValueError("Client header(s) `X-Initial-Header` already registered")

    mock_async_client.add_headers = AsyncMock(side_effect=mock_add_headers_async)

    with patch(
        "toolbox_core.sync_client.ToolboxClient", return_value=mock_async_client
    ):
        with ToolboxSyncClient(TEST_BASE_URL, client_headers=initial_headers) as client:
            # The initial headers are passed to the (mocked) ToolboxClient constructor.
            # Now, try to add a duplicate via ToolboxSyncClient.add_headers
            with pytest.raises(
                ValueError,
                match="Client header\\(s\\) `X-Initial-Header` already registered",
            ):
                client.add_headers({"X-Initial-Header": "another_value"})


def test_load_tool_raises_if_loop_or_thread_none():
    """
    Tests that load_tool and load_toolset raise ValueError if the class-level
    event loop or thread is None when accessed.
    This condition is hard to achieve normally due to __init__ and the fixture,
    so we manually unset them after client creation.
    """
    # Client initialization will set up the class loop and thread via the fixture logic.
    client = ToolboxSyncClient(TEST_BASE_URL)

    # Save the properly initialized loop/thread from the class
    original_class_loop = ToolboxSyncClient._ToolboxSyncClient__loop
    original_class_thread = ToolboxSyncClient._ToolboxSyncClient__thread
    assert original_class_loop is not None
    assert original_class_thread is not None

    # Manually break the class's loop to trigger the error condition in load_tool
    ToolboxSyncClient._ToolboxSyncClient__loop = None
    with pytest.raises(ValueError, match="Background loop or thread cannot be None."):
        client.load_tool("any_tool_should_fail")

    # Restore the loop for the next check (or cleanup)
    ToolboxSyncClient._ToolboxSyncClient__loop = original_class_loop

    # Manually break the class's thread
    ToolboxSyncClient._ToolboxSyncClient__thread = None
    with pytest.raises(ValueError, match="Background loop or thread cannot be None."):
        client.load_toolset("any_toolset_should_fail")

    # Restore both for fixture cleanup or subsequent operations (like client.close)
    ToolboxSyncClient._ToolboxSyncClient__loop = original_class_loop
    ToolboxSyncClient._ToolboxSyncClient__thread = original_class_thread

    client.close()  # Clean up the async_client session


class TestSyncAuth:
    @pytest.fixture
    def expected_header_token(self):
        return "sync_auth_token_for_testing"

    @pytest.fixture
    def tool_name_auth(self):
        return "sync_auth_tool1"

    def test_auth_with_load_tool_success(
        self,
        tool_name_auth,
        expected_header_token,
        test_tool_auth_schema,
        aioresponses,
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )

        def require_headers_callback(url, **kwargs):
            assert (
                kwargs["headers"].get("my-auth-service_token") == expected_header_token
            )
            return CallbackResult(status=200, payload={"result": "auth_ok"})

        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}/invoke",
            callback=require_headers_callback,
        )

        with ToolboxSyncClient(TEST_BASE_URL) as client:

            def token_handler():
                return expected_header_token

            tool = client.load_tool(
                tool_name_auth, auth_token_getters={"my-auth-service": token_handler}
            )
            result = tool(argA=5)  # argB is the authed param in schema
            assert result == "auth_ok"

    def test_auth_with_add_token_success(
        self,
        tool_name_auth,
        expected_header_token,
        test_tool_auth_schema,
        aioresponses,
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )

        def require_headers_callback(url, **kwargs):
            assert (
                kwargs["headers"].get("my-auth-service_token") == expected_header_token
            )
            return CallbackResult(status=200, payload={"result": "auth_ok"})

        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}/invoke",
            callback=require_headers_callback,
        )

        with ToolboxSyncClient(TEST_BASE_URL) as client:

            def token_handler():
                return expected_header_token

            tool = client.load_tool(tool_name_auth)
            authed_tool = tool.add_auth_token_getters(
                {"my-auth-service": token_handler}
            )
            result = authed_tool(argA=10)
            assert result == "auth_ok"

    def test_auth_with_load_tool_fail_no_token(
        self, tool_name_auth, test_tool_auth_schema, aioresponses
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )
        aioresponses.post(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}/invoke",
            payload={"error": "Missing token"},
            status=400,  # Simulate server error
        )

        with ToolboxSyncClient(TEST_BASE_URL) as client:
            tool = client.load_tool(tool_name_auth)
            # Invocation should fail
            with pytest.raises(
                ValueError,
                match="One or more of the following authn services are required to invoke this tool: my-auth-service",
            ):  # Match error from client
                tool(argA=15, argB=True)

    def test_add_auth_token_getters_duplicate_fail(
        self, tool_name_auth, test_tool_auth_schema, aioresponses
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )
        # No invoke needed for this test, it's about configuring the tool

        with ToolboxSyncClient(TEST_BASE_URL) as client:
            AUTH_SERVICE = "my-auth-service"
            tool = client.load_tool(tool_name_auth)

            # First addition should work
            authed_tool = tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token1"})
            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` already registered in tool `{tool_name_auth}`.",
            ):
                authed_tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token2"})

    def test_add_auth_token_getters_missing_fail(
        self, tool_name_auth, test_tool_auth_schema, aioresponses
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )

        with ToolboxSyncClient(TEST_BASE_URL) as client:
            UNUSED_AUTH_SERVICE = "xmy-auth-service"
            tool = client.load_tool(tool_name_auth)

            with pytest.raises(
                ValueError,
                match=f"Authentication source\\(s\\) `{UNUSED_AUTH_SERVICE}` unused by tool `{tool_name_auth}`.",
            ):
                tool.add_auth_token_getters({UNUSED_AUTH_SERVICE: lambda: "token"})

    def test_constructor_getters_missing_fail(
        self, tool_name_auth, test_tool_auth_schema, aioresponses
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        aioresponses.get(
            f"{TEST_BASE_URL}/api/tool/{tool_name_auth}",
            payload=manifest.model_dump(),
            status=200,
        )

        with ToolboxSyncClient(TEST_BASE_URL) as client:
            UNUSED_AUTH_SERVICE = "xmy-auth-service-constructor"
            with pytest.raises(
                ValueError,
                match=f"Validation failed for tool '{tool_name_auth}': unused auth tokens: {UNUSED_AUTH_SERVICE}.",
            ):
                client.load_tool(
                    tool_name_auth,
                    auth_token_getters={UNUSED_AUTH_SERVICE: lambda: "token"},
                )
