from functools import partial

import google.auth
from google.auth._credentials_async import Credentials
from google.auth._default_async import default_async
from google.auth.transport import _aiohttp_requests
from google.auth.transport.requests import AuthorizedSession, Request


async def aget_google_id_token():
    creds, _ = default_async()
    await creds.refresh(_aiohttp_requests.Request())
    creds.before_request = partial(Credentials.before_request, creds)
    token = creds.id_token
    return f"Bearer {token}"


def get_google_id_token():
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials)
    request = Request(session)
    credentials.refresh(request)
    token = credentials.id_token
    return f"Bearer {token}"
