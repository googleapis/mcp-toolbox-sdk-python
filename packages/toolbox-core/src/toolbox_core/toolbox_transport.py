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

from aiohttp import ClientSession

from .itransport import ITransport
from .protocol import ManifestSchema


class ToolboxHttpTransport(ITransport):
    """Transport for the native Toolbox protocol."""

    def __init__(self, base_url: str, session: ClientSession, manage_session: bool):
        self.__base_url = base_url
        self.__session = session
        self.__manage_session = manage_session

    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        url = f"{self.__base_url}/api/tool/{tool_name}"
        async with self.__session.get(url, headers=headers) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} ({response.reason}). Server response: {error_text}"
                )
            json = await response.json()
        return ManifestSchema(**json)

    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        url = f"{self.__base_url}/api/toolset/{toolset_name or ''}"
        async with self.__session.get(url, headers=headers) as response:
            if not response.ok:
                error_text = await response.text()
                raise RuntimeError(
                    f"API request failed with status {response.status} ({response.reason}). Server response: {error_text}"
                )
            json = await response.json()
        return ManifestSchema(**json)

    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> dict:
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
        return body

    async def close(self):
        if self.__manage_session and not self.__session.closed:
            await self.__session.close()
