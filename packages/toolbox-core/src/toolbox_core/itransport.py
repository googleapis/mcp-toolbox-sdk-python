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

from abc import ABC, abstractmethod
from typing import Mapping, Optional

from .protocol import ManifestSchema


class ITransport(ABC):
    """Defines the contract for a 'smart' transport that handles both
    protocol formatting and network communication.
    """

    @property
    @abstractmethod
    def base_url(self) -> str:
        """The base URL for the transport."""
        pass

    @abstractmethod
    async def tool_get(
        self, tool_name: str, headers: Optional[Mapping[str, str]] = None
    ) -> ManifestSchema:
        """Gets a single tool from the server."""
        pass

    @abstractmethod
    async def tools_list(
        self,
        toolset_name: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> ManifestSchema:
        """Lists available tools from the server."""
        pass

    @abstractmethod
    async def tool_invoke(
        self, tool_name: str, arguments: dict, headers: Mapping[str, str]
    ) -> str:
        """Invokes a specific tool on the server."""
        pass

    @abstractmethod
    async def close(self):
        """Closes any underlying connections."""
        pass
