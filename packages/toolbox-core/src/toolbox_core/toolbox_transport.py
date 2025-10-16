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

from typing import Mapping, Optional
from warnings import warn

from aiohttp import ClientSession

from .itransport import ITransport
from .protocol import ManifestSchema


class ToolboxTransport(ITransport):
    """Transport for the native Toolbox protocol."""

    def __init__(self, base_url: str, session: Optional[ClientSession]):
        self.__base_url = base_url

        # If no aiohttp.ClientSession is provided, make our own
        self.__manage_session = False
        if session is not None:
            self.__session = session
        else:
            self.__manage_session = True
            self.__session = ClientSession()

    @property
    def base_url(self) -> str:
        """The base URL for the transport."""
        return self.__base_url

    async def __get_manifest(
        self, url: str, headers: Optional[Mapping[str, str]]
    ) -> ManifestSchema:
        """Helper method to perform GET requests and parse the ManifestSchema."""
        async with self.__session.get(url, headers=headers) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} ({response.reason}). Server response: {error_text}"
                )
            json = await response.json()
        return ManifestSchema(**json)

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        url = f"{self.__base_url}/api/tool/{tool_name}"
        return await self.__get_manifest(url, headers)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        url = f"{self.__base_url}/api/toolset/{toolset_name or ''}"
        return await self.__get_manifest(url, headers)

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        # ID tokens contain sensitive user information (claims). Transmitting
        # these over HTTP exposes the data to interception and unauthorized
        # access. Always use HTTPS to ensure secure communication and protect
        # user privacy.
        if self.base_url.startswith("http://") and headers:
            warn(
                "Sending data token over HTTP. User data may be exposed. Use HTTPS for secure communication."
            )
        url = f"{self.__base_url}/api/tool/{tool_name}/invoke"
        async with self.__session.post(
            url,
            json=arguments,
            headers=headers,
        ) as resp:
            body = await resp.json()
            if not resp.ok:
                err = body.get("error", f"unexpected status from server: {resp.status}")
                raise Exception(err)
        return body.get("result")

    async def close(self):
        if self.__manage_session and not self.__session.closed:
            await self.__session.close()
