from typing import Any

import httpx

BASE_URL = "https://www.simpleinout.com/api/v4"
TOKEN_URL = "https://www.simpleinout.com/oauth/token"


class SimpleInOutError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Simple In/Out API error {status_code}: {message}")


class SimpleInOutClient:
    """Async httpx client wrapping the Simple In/Out APIv4.

    Auth: OAuth2. The one-time interactive Authorization Code grant (a human
    logging in and granting access) is done out-of-band to obtain an initial
    refresh_token. From then on, this client only needs client_id +
    client_secret + refresh_token — it re-exchanges the refresh_token for a
    fresh access_token on every call (grant_type=refresh_token, no
    redirect_uri required for this grant), keeping the service stateless.
    """

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    async def _login(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )
        self._raise_for_status(resp)
        return resp.json()["access_token"]

    def _clean_params(self, params: dict | None) -> dict:
        if not params:
            return {}
        return {k: v for k, v in params.items() if v is not None}

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            token = await self._login(client)
            resp = await client.get(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=self._clean_params(params),
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 else None

    async def post(self, path: str, body: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            token = await self._login(client)
            resp = await client.post(
                f"{BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 else None

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise SimpleInOutError(resp.status_code, str(detail))
