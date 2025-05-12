from functools import partial
from google.auth._default_async import default_async
from google.auth.transport import _aiohttp_requests
import google.auth 
from google.auth.transport.requests import AuthorizedSession, Request 
from google.auth._credentials_async import Credentials


async def aget_google_id_token():
    creds, _ = default_async()
    await creds.refresh(_aiohttp_requests.Request())
    creds.before_request = partial(Credentials.before_request, creds)
    return creds.id_token

def get_google_id_token():
    credentials, _ = google.auth.default()
    session = AuthorizedSession(credentials) 
    request = Request(session) 
    credentials.refresh(request) 
    return credentials.id_token