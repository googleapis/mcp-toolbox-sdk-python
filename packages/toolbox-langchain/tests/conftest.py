# Copyright 2024 Google LLC
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

"""Contains pytest fixtures that are accessible from all
files present in the same directory."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import time
from typing import Generator

import google
import pytest
from google.auth import compute_engine
from google.cloud import secretmanager, storage


#### Define Utility Functions
def get_env_var(key: str) -> str:
    """Gets environment variables."""
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Must set env var {key}")
    return value


def access_secret_version(
    project_id: str, secret_id: str, version_id: str = "latest"
) -> str:
    """Accesses the payload of a given secret version from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def create_tmpfile(content: str) -> str:
    """Creates a temporary file with the given content."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as tmpfile:
        tmpfile.write(content)
        return tmpfile.name


def download_blob(
    bucket_name: str, source_blob_name: str, destination_file_name: str
) -> None:
    """Downloads a blob from a GCS bucket."""
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")


def get_toolbox_binary_url(toolbox_version: str) -> str:
    """Constructs the GCS path to the toolbox binary."""
    os_system = platform.system().lower()
    arch = (
        "arm64" if os_system == "darwin" and platform.machine() == "arm64" else "amd64"
    )
    ext = ".exe" if os_system == "windows" else ""
    return f"{toolbox_version}/{os_system}/{arch}/toolbox{ext}"


def get_auth_token(client_id: str) -> str:
    """Retrieves an authentication token"""
    request = google.auth.transport.requests.Request()
    credentials = compute_engine.IDTokenCredentials(
        request=request,
        target_audience=client_id,
        use_metadata_identity_endpoint=True,
    )
    if not credentials.valid:
        credentials.refresh(request)
    return credentials.token


#### Define Fixtures
@pytest.fixture(scope="session")
def project_id() -> str:
    return get_env_var("GOOGLE_CLOUD_PROJECT")


@pytest.fixture(scope="session")
def toolbox_version() -> str:
    return get_env_var("TOOLBOX_VERSION")


@pytest.fixture(scope="session")
def tools_file_path(project_id: str) -> Generator[str]:
    """Provides a temporary file path containing the tools manifest."""
    tools_manifest = access_secret_version(
        project_id=project_id,
        secret_id="sdk_testing_tools",
        version_id=os.environ.get("TOOLBOX_MANIFEST_VERSION", "latest"),
    )
    tools_file_path = create_tmpfile(tools_manifest)
    yield tools_file_path
    os.remove(tools_file_path)


@pytest.fixture(scope="session")
def auth_token1(project_id: str) -> str:
    client_id = access_secret_version(
        project_id=project_id, secret_id="sdk_testing_client1"
    )
    return get_auth_token(client_id)


@pytest.fixture(scope="session")
def auth_token2(project_id: str) -> str:
    client_id = access_secret_version(
        project_id=project_id, secret_id="sdk_testing_client2"
    )
    return get_auth_token(client_id)


@pytest.fixture(scope="session")
def toolbox_server(toolbox_version: str, tools_file_path: str) -> Generator[None]:
    """Starts the toolbox server as a subprocess."""
    print("Downloading toolbox binary from gcs bucket...")
    source_blob_name = get_toolbox_binary_url(toolbox_version)
    bucket_name = (
        "mcp-toolbox-for-databases-dev"
        if toolbox_version in ("main", "mcp-v202606")
        else "mcp-toolbox-for-databases"
    )
    download_blob(bucket_name, source_blob_name, "toolbox")
    print("Toolbox binary downloaded successfully.")
    try:
        print("Opening toolbox server process...")
        # Make toolbox executable
        os.chmod("toolbox", 0o700)
        # Run toolbox binary
        toolbox_server_1 = subprocess.Popen(
            ["./toolbox", "--port", "5000", "--tools-file", tools_file_path]
        )
        toolbox_server_2 = subprocess.Popen(
            [
                "./toolbox",
                "--port",
                "5001",
                "--tools-file",
                tools_file_path,
                "--enable-draft-specs",
            ]
        )

        # Wait for server to start
        # Retry logic with a timeout
        for _ in range(5):  # retries
            time.sleep(4)
            print("Checking if both toolbox servers are successfully started...")
            if toolbox_server_1.poll() is None and toolbox_server_2.poll() is None:
                print("Toolbox servers started successfully.")
                break
        else:
            raise RuntimeError("Toolbox servers failed to start after 5 retries.")
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode("utf-8"))
        print(e.stdout.decode("utf-8"))
        raise RuntimeError(f"{e}\n\n{e.stderr.decode('utf-8')}") from e
    yield

    # Clean up toolbox server
    toolbox_server_1.terminate()
    toolbox_server_2.terminate()
    toolbox_server_1.wait()
    toolbox_server_2.wait()


@pytest.fixture(
    params=["http://localhost:5000", "http://localhost:5001"], scope="session"
)
def toolbox_server_url(request) -> str:
    return request.param


@pytest.fixture(autouse=True)
def patch_toolbox_client_url(toolbox_server_url):
    from toolbox_core.client import ToolboxClient

    original_init = ToolboxClient.__init__

    def new_init(self, url="http://localhost:5000", *args, **kwargs):
        if url == "http://localhost:5000":
            url = toolbox_server_url
        original_init(self, url, *args, **kwargs)

    from unittest.mock import patch

    with patch.object(ToolboxClient, "__init__", new_init, create=True):
        yield
