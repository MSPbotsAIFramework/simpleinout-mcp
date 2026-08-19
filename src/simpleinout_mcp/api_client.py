import asyncio
from typing import Any

import httpx

from ._json import error_envelope

BASE_URL = "https://www.simpleinout.com/api/v4"
TOKEN_URL = "https://www.simpleinout.com/oauth/token"

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_MAX_BACKOFF_SECONDS = 20.0

# One shared connection pool for the process lifetime. No credentials are
# ever stored on it — client_id/secret/refresh_token are passed per-request
# via SimpleInOutClient instances built from per-request header values (see
# server.py's contextvar-based credential isolation, which is what actually
# keeps tenants apart).
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True)
    return _http_client


# status_code -> (error code, retryable). status_code 0 means a network/
# connection-level failure (no response at all).
_STATUS_TO_CODE: dict[int, tuple[str, bool]] = {
    0: ("upstream_error", True),
    400: ("invalid_argument", False),
    401: ("unauthorized", False),
    403: ("unauthorized", False),
    404: ("not_found", False),
    422: ("invalid_argument", False),
    429: ("rate_limited", True),
}


def _classify(status_code: int) -> tuple[str, bool]:
    if status_code in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[status_code]
    if status_code >= 500:
        return "upstream_error", True
    return "invalid_argument", False


class SimpleInOutError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Simple In/Out API error {status_code}: {message}")

    def to_envelope(self) -> str:
        code, retryable = _classify(self.status_code)
        return error_envelope(code, self.message, retryable)


class SimpleInOutClient:
    """Async httpx client wrapping the Simple In/Out APIv4.

    Auth: OAuth2. The one-time interactive Authorization Code grant (a human
    logging in and granting access) is done out-of-band to obtain an initial
    refresh_token. From then on, this client only needs client_id +
    client_secret + refresh_token — it re-exchanges the refresh_token for a
    fresh access_token on every call (grant_type=refresh_token, no
    redirect_uri required for this grant), keeping the service stateless
    (no cross-request token caching — see server.py / SOP §3.4).

    Reuses the module-level connection pool (see _get_http_client) across
    every call made through this instance, rather than opening a new
    connection per request.
    """

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def _clean_params(self, params: dict | None) -> dict:
        if not params:
            return {}
        return {k: v for k, v in params.items() if v is not None}

    async def _login(self) -> str:
        resp = await self._send_with_retry(
            "POST",
            TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json_body={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )
        return resp.json()["access_token"]

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._call("GET", path, params=params)

    async def post(self, path: str, body: dict | None = None) -> Any:
        return await self._call("POST", path, json_body=body)

    async def _call(
        self, method: str, path: str, params: dict | None = None, json_body: Any = None
    ) -> Any:
        token = await self._login()
        headers = {"Authorization": f"Bearer {token}"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        resp = await self._send_with_retry(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            params=self._clean_params(params),
            json_body=json_body,
        )
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    async def _send_with_retry(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        json_body: Any = None,
    ) -> httpx.Response:
        client = _get_http_client()
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.request(
                    method, url, headers=headers, params=params, json=json_body
                )
            except httpx.RequestError as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(min(2**attempt, _MAX_BACKOFF_SECONDS))
                    continue
                raise SimpleInOutError(0, f"{e or type(e).__name__} (url={url})") from e

            if resp.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                delay = self._retry_delay(resp, attempt)
                await asyncio.sleep(delay)
                continue

            self._raise_for_status(resp)
            return resp

        # Unreachable in practice (loop always returns or raises above), but
        # keeps type checkers happy and guards against future edits.
        if last_exc:
            raise SimpleInOutError(0, f"{last_exc}") from last_exc
        raise SimpleInOutError(0, "request failed with no response")

    def _retry_delay(self, resp: httpx.Response, attempt: int) -> float:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), _MAX_BACKOFF_SECONDS)
            except ValueError:
                pass
        return min(2**attempt, _MAX_BACKOFF_SECONDS)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
                if isinstance(detail, dict):
                    msg = (
                        detail.get("message")
                        or detail.get("error_description")
                        or detail.get("error")
                        or str(detail)
                    )
                else:
                    msg = str(detail)
            except ValueError:
                msg = resp.text
            raise SimpleInOutError(resp.status_code, msg)
