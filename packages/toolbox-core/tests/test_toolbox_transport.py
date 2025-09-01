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

from typing import AsyncGenerator, Mapping, Optional, Union
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses

from toolbox_core.protocol import ManifestSchema
from toolbox_core.toolbox_transport import ToolboxTransport

TEST_BASE_URL = "http://fake-toolbox-server.com"
TEST_TOOL_NAME = "test_tool"


@pytest_asyncio.fixture
async def http_session() -> AsyncGenerator[ClientSession, None]:
    """Provides a real aiohttp ClientSession that is closed after the test."""
    async with ClientSession() as session:
        yield session


@pytest.fixture
def mock_manifest_dict() -> dict:
    """Provides a valid sample dictionary for a ManifestSchema response."""
    tool_definition = {
        "name": TEST_TOOL_NAME,
        "description": "A test tool",
        "parameters": [
            {
                "name": "param1",
                "type": "string",
                "description": "The first parameter.",
                "required": True,
            }
        ],
    }
    return {
        "serverVersion": "1.0.0",
        "tools": {TEST_TOOL_NAME: tool_definition},
    }


@pytest.mark.asyncio
async def test_base_url_property(http_session: ClientSession):
    """Tests that the base_url property returns the correct URL."""
    transport = ToolboxTransport(TEST_BASE_URL, http_session)
    assert transport.base_url == TEST_BASE_URL


@pytest.mark.asyncio
async def test_tool_get_success(http_session: ClientSession, mock_manifest_dict: dict):
    """Tests a successful tool_get call."""
    url = f"{TEST_BASE_URL}/api/tool/{TEST_TOOL_NAME}"
    headers = {"X-Test-Header": "value"}
    transport = ToolboxTransport(TEST_BASE_URL, http_session)

    with aioresponses() as m:
        m.get(url, status=200, payload=mock_manifest_dict)
        result = await transport.tool_get(TEST_TOOL_NAME, headers=headers)

        assert isinstance(result, ManifestSchema)
        assert result.serverVersion == "1.0.0"
        # FIX: Check for a valid attribute like 'description' instead of 'name'
        assert result.tools[TEST_TOOL_NAME].description == "A test tool"
        m.assert_called_once_with(url, headers=headers)


@pytest.mark.asyncio
async def test_tool_get_failure(http_session: ClientSession):
    """Tests a failing tool_get call and ensures it raises RuntimeError."""
    url = f"{TEST_BASE_URL}/api/tool/{TEST_TOOL_NAME}"
    transport = ToolboxTransport(TEST_BASE_URL, http_session)

    with aioresponses() as m:
        m.get(url, status=500, body="Internal Server Error")
        with pytest.raises(RuntimeError) as exc_info:
            await transport.tool_get(TEST_TOOL_NAME)

    assert "API request failed with status 500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "toolset_name, expected_path",
    [
        ("my_toolset", "/api/toolset/my_toolset"),
        (None, "/api/toolset/"),
    ],
)
async def test_tools_list_success(
    http_session: ClientSession,
    mock_manifest_dict: dict,
    toolset_name: Union[str, None],
    expected_path: str,
):
    """Tests successful tools_list calls with and without a toolset name."""
    url = f"{TEST_BASE_URL}{expected_path}"
    transport = ToolboxTransport(TEST_BASE_URL, http_session)

    with aioresponses() as m:
        m.get(url, status=200, payload=mock_manifest_dict)
        result = await transport.tools_list(toolset_name=toolset_name)

        assert isinstance(result, ManifestSchema)
        # FIX: Add headers=None to match the actual call signature
        m.assert_called_once_with(url, headers=None)


@pytest.mark.asyncio
async def test_tool_invoke_success(http_session: ClientSession):
    """Tests a successful tool_invoke call."""
    url = f"{TEST_BASE_URL}/api/tool/{TEST_TOOL_NAME}/invoke"
    args = {"param1": "value1"}
    headers = {"Authorization": "Bearer token"}
    response_payload = {"result": "success"}
    transport = ToolboxTransport(TEST_BASE_URL, http_session)

    with aioresponses() as m:
        m.post(url, status=200, payload=response_payload)
        result = await transport.tool_invoke(TEST_TOOL_NAME, args, headers)

        assert result == "success"
        m.assert_called_once_with(url, method="POST", json=args, headers=headers)


@pytest.mark.asyncio
async def test_tool_invoke_failure(http_session: ClientSession):
    """Tests a failing tool_invoke call where the server returns an error payload."""
    url = f"{TEST_BASE_URL}/api/tool/{TEST_TOOL_NAME}/invoke"
    response_payload = {"error": "Invalid arguments"}
    transport = ToolboxTransport(TEST_BASE_URL, http_session)

    with aioresponses() as m:
        m.post(url, status=400, payload=response_payload)
        with pytest.raises(Exception) as exc_info:
            await transport.tool_invoke(TEST_TOOL_NAME, {}, {})

    assert str(exc_info.value) == "Invalid arguments"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "base_url, headers, should_warn",
    [
        (
            "http://fake-toolbox-server.com",
            {"Authorization": "Bearer token"},
            True,
        ),
        (
            "https://fake-toolbox-server.com",
            {"Authorization": "Bearer token"},
            False,
        ),
        ("http://fake-toolbox-server.com", {}, False),
        ("http://fake-toolbox-server.com", None, False),
    ],
)
async def test_tool_invoke_http_warning(
    http_session: ClientSession,
    base_url: str,
    headers: Optional[Mapping[str, str]],
    should_warn: bool,
):
    """Tests the HTTP security warning logic in tool_invoke."""
    url = f"{base_url}/api/tool/{TEST_TOOL_NAME}/invoke"
    args = {"param1": "value1"}
    response_payload = {"result": "success"}
    transport = ToolboxTransport(base_url, http_session)

    with aioresponses() as m:
        m.post(url, status=200, payload=response_payload)

        if should_warn:
            with pytest.warns(UserWarning, match="Sending data token over HTTP"):
                await transport.tool_invoke(TEST_TOOL_NAME, args, headers)
        else:
            # By not using pytest.warns, we assert that no warnings are raised.
            # The test will fail if an unexpected UserWarning occurs.
            await transport.tool_invoke(TEST_TOOL_NAME, args, headers)


@pytest.mark.asyncio
async def test_close_does_not_close_unmanaged_session():
    """
    Tests that close() does NOT affect a session that was provided externally
    (i.e., an unmanaged session).
    """
    mock_session = AsyncMock(spec=ClientSession)
    mock_session.closed = False

    transport = ToolboxTransport(TEST_BASE_URL, mock_session)
    await transport.close()
    mock_session.close.assert_not_called()


@pytest.mark.asyncio
async def test_close_closes_managed_session():
    """
    Tests that close() successfully closes a session that was created and
    managed internally by the transport.
    """
    transport = ToolboxTransport(TEST_BASE_URL, session=None)
    # Access the internal session before closing to check its state
    internal_session = transport._ToolboxTransport__session
    assert internal_session.closed is False

    await transport.close()
    internal_session = transport._ToolboxTransport__session
    assert internal_session.closed is True
