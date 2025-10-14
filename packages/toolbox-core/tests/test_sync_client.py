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
from typing import Mapping, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from toolbox_core.client import ToolboxClient
from toolbox_core.itransport import ITransport
from toolbox_core.protocol import ManifestSchema, ParameterSchema, ToolSchema
from toolbox_core.sync_client import ToolboxSyncClient
from toolbox_core.sync_tool import ToolboxSyncTool

TEST_BASE_URL = "http://toolbox.example.com"


class MockSyncTransport(ITransport):
    """A mock transport for testing the ToolboxClient."""

    def __init__(self, base_url: str):
        self._base_url = base_url
        self.tool_get_mock = AsyncMock()
        self.tools_list_mock = AsyncMock()
        self.tool_invoke_mock = AsyncMock()
        self.close_mock = AsyncMock()

    @property
    def base_url(self) -> str:
        return self._base_url

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        return await self.tool_get_mock(tool_name, headers)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        return await self.tools_list_mock(toolset_name, headers)

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        return await self.tool_invoke_mock(tool_name, arguments, headers)

    async def close(self):
        await self.close_mock()


@pytest.fixture
def mock_transport() -> MockSyncTransport:
    """Provides a mock transport instance."""
    return MockSyncTransport(TEST_BASE_URL)


@pytest.fixture
def sync_client_environment():
    """
    Ensures a clean environment for ToolboxSyncClient class-level resources.
    It resets the class-level event loop and thread before the test
    and stops them after the test. This is crucial for test isolation
    due to ToolboxSyncClient's use of class-level loop/thread.
    """
    # Save current state if any (more of a defensive measure)
    original_loop = getattr(ToolboxSyncClient, "_ToolboxSyncClient__loop", None)
    original_thread = getattr(ToolboxSyncClient, "_ToolboxSyncClient__thread", None)

    # Force reset class state before the test.
    # This ensures any client created will start a new loop/thread.

    # Ensure no loop/thread is running from a previous misbehaving test or setup
    if original_loop and original_loop.is_running():
        original_loop.call_soon_threadsafe(original_loop.stop)
        if original_thread and original_thread.is_alive():
            original_thread.join()
        ToolboxSyncClient._ToolboxSyncClient__loop = None
        ToolboxSyncClient._ToolboxSyncClient__thread = None

    ToolboxSyncClient._ToolboxSyncClient__loop = None
    ToolboxSyncClient._ToolboxSyncClient__thread = None

    yield

    # Teardown: stop the loop and join the thread created *during* the test.
    test_loop = getattr(ToolboxSyncClient, "_ToolboxSyncClient__loop", None)
    test_thread = getattr(ToolboxSyncClient, "_ToolboxSyncClient__thread", None)

    if test_loop and test_loop.is_running():
        test_loop.call_soon_threadsafe(test_loop.stop)
    if test_thread and test_thread.is_alive():
        test_thread.join()

    # Explicitly set to None to ensure a clean state for the next fixture use/test.
    ToolboxSyncClient._ToolboxSyncClient__loop = None
    ToolboxSyncClient._ToolboxSyncClient__thread = None


@pytest.fixture
def sync_client(sync_client_environment):
    """
    Provides a ToolboxSyncClient instance within an isolated environment.
    The client's underlying async session is automatically closed after the test.
    The class-level loop/thread are managed by sync_client_environment.
    """
    client = ToolboxSyncClient(TEST_BASE_URL)

    yield client

    client.close()  # Closes the async_client's session.
    # Loop/thread shutdown is handled by sync_client_environment's teardown.


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


def test_sync_load_tool_success(test_tool_str_schema, sync_client, mock_transport):
    TOOL_NAME = "test_tool_sync_1"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str_schema}
    )
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.return_value = "sync_tool_ok"
    sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
        mock_transport
    )

    loaded_tool = sync_client.load_tool(TOOL_NAME)

    assert callable(loaded_tool)
    assert isinstance(loaded_tool, ToolboxSyncTool)
    assert loaded_tool.__name__ == TOOL_NAME
    assert test_tool_str_schema.description in loaded_tool.__doc__
    sig = inspect.signature(loaded_tool)
    assert list(sig.parameters.keys()) == [
        p.name for p in test_tool_str_schema.parameters
    ]
    result = loaded_tool(param1="some value")
    assert result == "sync_tool_ok"


def test_sync_load_toolset_success(
    test_tool_str_schema, test_tool_int_bool_schema, sync_client, mock_transport
):
    TOOLSET_NAME = "my_sync_toolset"
    TOOL1_NAME = "sync_tool1"
    TOOL2_NAME = "sync_tool2"
    tools_definition = {
        TOOL1_NAME: test_tool_str_schema,
        TOOL2_NAME: test_tool_int_bool_schema,
    }
    manifest = ManifestSchema(serverVersion="0.0.0", tools=tools_definition)
    mock_transport.tools_list_mock.return_value = manifest
    mock_transport.tool_invoke_mock.side_effect = ["sync_tool1_ok", "sync_tool2_ok"]
    sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
        mock_transport
    )

    tools = sync_client.load_toolset(TOOLSET_NAME)

    assert isinstance(tools, list)
    assert len(tools) == len(tools_definition)
    assert all(isinstance(t, ToolboxSyncTool) for t in tools)
    assert {t.__name__ for t in tools} == tools_definition.keys()
    tool1 = next(t for t in tools if t.__name__ == TOOL1_NAME)
    result1 = tool1(param1="hello")
    assert result1 == f"{TOOL1_NAME}_ok"


def test_sync_invoke_tool_server_error(
    test_tool_str_schema, sync_client, mock_transport
):
    TOOL_NAME = "sync_server_error_tool"
    ERROR_MESSAGE = "Simulated Server Error for Sync Client"
    manifest = ManifestSchema(
        serverVersion="0.0.0", tools={TOOL_NAME: test_tool_str_schema}
    )
    mock_transport.tool_get_mock.return_value = manifest
    mock_transport.tool_invoke_mock.side_effect = Exception(ERROR_MESSAGE)
    sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
        mock_transport
    )

    loaded_tool = sync_client.load_tool(TOOL_NAME)
    with pytest.raises(Exception, match=ERROR_MESSAGE):
        loaded_tool(param1="some input")


def test_sync_load_tool_not_found_in_manifest(
    test_tool_str_schema, sync_client, mock_transport
):
    ACTUAL_TOOL_IN_MANIFEST = "actual_tool_sync_abc"
    REQUESTED_TOOL_NAME = "non_existent_tool_sync_xyz"
    mismatched_manifest = ManifestSchema(
        serverVersion="0.0.0", tools={ACTUAL_TOOL_IN_MANIFEST: test_tool_str_schema}
    )
    mock_transport.tool_get_mock.return_value = mismatched_manifest
    sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
        mock_transport
    )

    with pytest.raises(
        ValueError,
        match=f"Tool '{REQUESTED_TOOL_NAME}' not found!",
    ):
        sync_client.load_tool(REQUESTED_TOOL_NAME)


class TestSyncClientLifecycle:
    """Tests for ToolboxSyncClient's specific lifecycle and internal management."""

    def test_sync_client_creation_in_isolated_env(self, sync_client):
        """Tests that a client is initialized correctly by the sync_client fixture."""
        assert (
            sync_client._ToolboxSyncClient__loop is not None
        ), "Loop should be created"
        assert (
            sync_client._ToolboxSyncClient__thread is not None
        ), "Thread should be created"
        assert (
            sync_client._ToolboxSyncClient__thread.is_alive()
        ), "Thread should be running"
        assert isinstance(
            sync_client._ToolboxSyncClient__async_client, ToolboxClient
        ), "Async client should be ToolboxClient instance"

    @pytest.mark.usefixtures("sync_client_environment")
    def test_sync_client_context_manager(self, tool_schema_minimal, mock_transport):
        """
        Tests the context manager (__enter__ and __exit__) functionality.
        The sync_client_environment ensures loop/thread cleanup.
        """
        with patch.object(
            ToolboxSyncClient, "close", wraps=ToolboxSyncClient.close, autospec=True
        ) as mock_close_method:
            with ToolboxSyncClient(TEST_BASE_URL) as client:
                client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
                    mock_transport
                )
                assert isinstance(client, ToolboxSyncClient)
                manifest = ManifestSchema(
                    serverVersion="0.0.0",
                    tools={"dummy_tool_ctx": tool_schema_minimal},
                )
                mock_transport.tool_get_mock.return_value = manifest
                client.load_tool("dummy_tool_ctx")
            mock_close_method.assert_called_once()

        with patch.object(
            ToolboxSyncClient, "close", wraps=ToolboxSyncClient.close, autospec=True
        ) as mock_close_method_exc:
            with pytest.raises(ValueError, match="Test exception"):
                with ToolboxSyncClient(TEST_BASE_URL) as client_exc:
                    raise ValueError("Test exception")
            mock_close_method_exc.assert_called_once()

    @pytest.mark.usefixtures("sync_client_environment")
    def test_load_tool_raises_if_loop_or_thread_none(self):
        """
        Tests that load_tool and load_toolset raise ValueError if the class-level
        event loop or thread is None. sync_client_environment ensures a clean
        slate before this test, and client creation will set up the loop/thread.
        """
        client = ToolboxSyncClient(TEST_BASE_URL)  # Loop/thread are started here.

        original_class_loop = ToolboxSyncClient._ToolboxSyncClient__loop
        original_class_thread = ToolboxSyncClient._ToolboxSyncClient__thread
        assert (
            original_class_loop is not None
        ), "Loop should have been created by client init"
        assert (
            original_class_thread is not None
        ), "Thread should have been created by client init"

        # Manually break the class's loop to trigger the error condition in load_tool
        ToolboxSyncClient._ToolboxSyncClient__loop = None
        with pytest.raises(
            ValueError, match="Background loop or thread cannot be None."
        ):
            client.load_tool("any_tool_should_fail")
        ToolboxSyncClient._ToolboxSyncClient__loop = (
            original_class_loop  # Restore for next check
        )

        ToolboxSyncClient._ToolboxSyncClient__thread = None
        with pytest.raises(
            ValueError, match="Background loop or thread cannot be None."
        ):
            client.load_toolset("any_toolset_should_fail")
        ToolboxSyncClient._ToolboxSyncClient__thread = original_class_thread  # Restore

        client.close()  # Clean up manually created client
        # sync_client_environment will handle the final cleanup of original_class_loop/thread.


class TestSyncClientHeaders:
    """Additive tests for client header functionality specific to ToolboxSyncClient if any,
    or counterparts to async client header tests."""

    def test_sync_add_headers_success(
        self, test_tool_str_schema, sync_client, mock_transport
    ):
        tool_name = "tool_after_add_headers_sync"
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name: test_tool_str_schema}
        )
        expected_payload = {"result": "added_sync_ok"}
        headers_to_add = {"X-Custom-SyncHeader": "sync_value"}

        mock_transport.tool_get_mock.return_value = manifest
        mock_transport.tool_invoke_mock.return_value = "added_sync_ok"
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        with pytest.warns(
            DeprecationWarning,
            match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
        ):
            sync_client.add_headers(headers_to_add)

        tool = sync_client.load_tool(tool_name)
        result = tool(param1="test")
        assert result == expected_payload["result"]

    def test_sync_add_headers_duplicate_fail(self):
        """Tests that adding a duplicate header via add_headers raises ValueError (from async client)."""
        initial_headers = {"X-Initial-Header": "initial_value"}
        mock_async_client = AsyncMock(spec=ToolboxClient)

        # Configure add_headers to simulate the ValueError from ToolboxClient
        def mock_add_headers(headers):
            # Simulate ToolboxClient's check
            if "X-Initial-Header" in headers:
                raise ValueError(
                    "Client header(s) `X-Initial-Header` already registered"
                )

        mock_async_client.add_headers = Mock(side_effect=mock_add_headers)

        with patch(
            "toolbox_core.sync_client.ToolboxClient", return_value=mock_async_client
        ):
            with ToolboxSyncClient(
                TEST_BASE_URL, client_headers=initial_headers
            ) as client:
                with pytest.warns(
                    DeprecationWarning,
                    match="Use the `client_headers` parameter in the ToolboxClient constructor instead.",
                ):
                    with pytest.raises(
                        ValueError,
                        match="Client header\\(s\\) `X-Initial-Header` already registered",
                    ):
                        client.add_headers({"X-Initial-Header": "another_value"})


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
        sync_client,
        mock_transport,
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        mock_transport.tool_invoke_mock.return_value = "auth_ok"
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        def token_handler():
            return expected_header_token

        tool = sync_client.load_tool(
            tool_name_auth, auth_token_getters={"my-auth-service": token_handler}
        )
        result = tool(argA=5)
        assert result == "auth_ok"

    def test_auth_with_add_token_success(
        self,
        tool_name_auth,
        expected_header_token,
        test_tool_auth_schema,
        sync_client,
        mock_transport,
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        mock_transport.tool_invoke_mock.return_value = "auth_ok"
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        def token_handler():
            return expected_header_token

        tool = sync_client.load_tool(tool_name_auth)
        authed_tool = tool.add_auth_token_getters({"my-auth-service": token_handler})
        result = authed_tool(argA=10)
        assert result == "auth_ok"

    def test_auth_with_load_tool_fail_no_token(
        self, tool_name_auth, test_tool_auth_schema, sync_client, mock_transport
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        tool = sync_client.load_tool(tool_name_auth)
        with pytest.raises(
            PermissionError,
            match="One or more of the following authn services are required to invoke this tool: my-auth-service",
        ):
            tool(argA=15, argB=True)

    def test_add_auth_token_getters_duplicate_fail(
        self, tool_name_auth, test_tool_auth_schema, sync_client, mock_transport
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        AUTH_SERVICE = "my-auth-service"
        tool = sync_client.load_tool(tool_name_auth)
        authed_tool = tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token1"})
        with pytest.raises(
            ValueError,
            match=f"Authentication source\\(s\\) `{AUTH_SERVICE}` already registered in tool `{tool_name_auth}`.",
        ):
            authed_tool.add_auth_token_getters({AUTH_SERVICE: lambda: "token2"})

    def test_add_auth_token_getters_missing_fail(
        self, tool_name_auth, test_tool_auth_schema, sync_client, mock_transport
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        UNUSED_AUTH_SERVICE = "xmy-auth-service"
        tool = sync_client.load_tool(tool_name_auth)
        with pytest.raises(
            ValueError,
            match=f"Authentication source\\(s\\) `{UNUSED_AUTH_SERVICE}` unused by tool `{tool_name_auth}`.",
        ):
            tool.add_auth_token_getters({UNUSED_AUTH_SERVICE: lambda: "token"})

    def test_constructor_getters_missing_fail(
        self, tool_name_auth, test_tool_auth_schema, sync_client, mock_transport
    ):
        manifest = ManifestSchema(
            serverVersion="0.0.0", tools={tool_name_auth: test_tool_auth_schema}
        )
        mock_transport.tool_get_mock.return_value = manifest
        sync_client._ToolboxSyncClient__async_client._ToolboxClient__transport = (
            mock_transport
        )

        UNUSED_AUTH_SERVICE = "xmy-auth-service-constructor"
        with pytest.raises(
            ValueError,
            match=f"Validation failed for tool '{tool_name_auth}': unused auth tokens: {UNUSED_AUTH_SERVICE}.",
        ):
            sync_client.load_tool(
                tool_name_auth,
                auth_token_getters={UNUSED_AUTH_SERVICE: lambda: "token"},
            )
