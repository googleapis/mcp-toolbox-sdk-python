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

# The tokens obtained by these functions are formatted as "Bearer" tokens
# and are intended to be passed in the "Authorization" header of HTTP requests.
#
# Example User Experience:
# from toolbox_core import auth_methods
#
# auth_token_provider = auth_methods.aget_google_id_token
# toolbox = ToolboxClient(
#     URL,
#     client_headers={"Authorization": auth_token_provider},
# )
# tools = await toolbox.load_toolset()


from functools import partial

import google.auth
from google.auth._credentials_async import Credentials
from google.auth._default_async import default_async
from google.auth.transport import _aiohttp_requests
from google.auth.transport.requests import AuthorizedSession, Request


async def aget_google_id_token():
    """
    Asynchronously fetches a Google ID token.

    The token is formatted as a 'Bearer' token string and is suitable for use
    in an HTTP Authorization header. This function uses Application Default
    Credentials.

    Returns:
        A string in the format "Bearer <google_id_token>".
    """
    creds, _ = default_async()
    await creds.refresh(_aiohttp_requests.Request())
    creds.before_request = partial(Credentials.before_request, creds)
    token = creds.id_token
    return f"Bearer {token}"


def get_google_id_token():
    """
    Synchronously fetches a Google ID token.

    The token is formatted as a 'Bearer' token string and is suitable for use
    in an HTTP Authorization header. This function uses Application Default
    Credentials.

    Returns:
        A string in the format "Bearer <google_id_token>".
    """
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)
    credentials.refresh(request)
    token = credentials.id_token
    return f"Bearer {token}"
