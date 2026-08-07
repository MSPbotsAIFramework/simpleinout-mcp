import contextvars
import sys
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import SimpleInOutClient
from .config import Settings

_gateway_creds_var: contextvars.ContextVar[tuple[str, str, str] | None] = contextvars.ContextVar(
    "simpleinout_gateway_creds", default=None
)


def get_client_from_context(settings: Settings) -> SimpleInOutClient | None:
    if settings.auth_mode == "gateway":
        creds = _gateway_creds_var.get()
        if creds is None:
            return None
        client_id, client_secret, refresh_token = creds
    else:
        client_id = settings.simpleinout_client_id
        client_secret = settings.simpleinout_client_secret
        refresh_token = settings.simpleinout_refresh_token

    if not client_id or not client_secret or not refresh_token:
        return None
    return SimpleInOutClient(client_id, client_secret, refresh_token)


class GatewayTokenMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        client_id = request.headers.get(self.settings.simpleinout_client_id_header.lower())
        client_secret = request.headers.get(self.settings.simpleinout_client_secret_header.lower())
        refresh_token = request.headers.get(self.settings.simpleinout_refresh_token_header.lower())
        if not client_id or not client_secret or not refresh_token:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": (
                        f"Gateway mode requires the {self.settings.simpleinout_client_id_header}, "
                        f"{self.settings.simpleinout_client_secret_header}, and "
                        f"{self.settings.simpleinout_refresh_token_header} headers"
                    ),
                    "required_headers": [
                        self.settings.simpleinout_client_id_header,
                        self.settings.simpleinout_client_secret_header,
                        self.settings.simpleinout_refresh_token_header,
                    ],
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        ctx_token = _gateway_creds_var.set((client_id, client_secret, refresh_token))
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_creds_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name="simpleinout-mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    client_factory: Callable[[], SimpleInOutClient | None] = lambda: get_client_from_context(settings)

    if not settings.has_credentials:
        @mcp.tool()
        async def simpleinout_test_connection() -> str:
            """Test Simple In/Out API connection. Shows configuration requirements when credentials are missing."""
            return (
                "Error: Missing Simple In/Out credentials.\n\n"
                "Set the required environment variables:\n"
                "  SIMPLEINOUT_CLIENT_ID=...\n"
                "  SIMPLEINOUT_CLIENT_SECRET=...\n"
                "  SIMPLEINOUT_REFRESH_TOKEN=...\n\n"
                "Or use gateway mode (per-request credentials):\n"
                "  AUTH_MODE=gateway\n"
                f"  Send headers: {settings.simpleinout_client_id_header}, "
                f"{settings.simpleinout_client_secret_header}, {settings.simpleinout_refresh_token_header}"
            )

        print(
            "Warning: No Simple In/Out credentials found. Only the diagnostic tool is available.",
            file=sys.stderr,
        )
        return mcp

    from .tools import inout

    inout.register(mcp, client_factory)

    return mcp
