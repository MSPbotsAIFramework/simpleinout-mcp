import contextvars

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import SimpleInOutClient
from .config import Settings

# Per-request credential isolation via contextvars.
# GatewayTokenMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent requests from
# different tenants are isolated from one another.
_gateway_creds_var: contextvars.ContextVar[tuple[str, str, str] | None] = contextvars.ContextVar(
    "simpleinout_gateway_creds", default=None
)


def get_client_from_context(settings: Settings) -> SimpleInOutClient | None:
    """Resolve the active SimpleInOutClient for the current request context."""
    creds = _gateway_creds_var.get()
    if creds is None:
        return None
    client_id, client_secret, refresh_token = creds
    return SimpleInOutClient(client_id, client_secret, refresh_token)


class GatewayTokenMiddleware:
    """ASGI middleware.

    Reads the three Simple In/Out credential headers (all required) from
    request headers and stores them in the contextvar. Returns 401 if any
    is missing on /mcp requests. Credentials never fall back to an
    environment variable (SOP §3.1) — a request without all three headers
    simply has no client available (see get_client_from_context).
    """

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
            required = [
                self.settings.simpleinout_client_id_header,
                self.settings.simpleinout_client_secret_header,
                self.settings.simpleinout_refresh_token_header,
            ]
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": f"This server requires the {', '.join(required)} headers",
                    "required_headers": required,
                    "optional_headers": [],
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
    """Build the FastMCP server instance and register all Simple In/Out tools."""
    # DNS-rebinding protection is a browser-oriented safeguard that rejects
    # non-localhost Host headers with 421. Disable it so the server works
    # correctly behind a reverse proxy or docker network.
    mcp = FastMCP(
        name="simpleinout-mcp",
        instructions=(
            "Simple In/Out is a staff in/out status board: employees check "
            'in/out with a status ("in", "remote", "busy", "break", "out", '
            '"sick", "vacation") and managers see live and historical status '
            "across the company. Core entities: company, users (with roles "
            "and group membership), and status history (per-user or "
            "company-wide). Supporting config: groups, beacons (Bluetooth "
            "presence), geofences, Wi-Fi networks (automatic presence "
            "detection), announcements, and roles. Typical flow: "
            "simpleinout_list_users or simpleinout_get_current_user to find "
            "a person, then simpleinout_list_user_statuses or "
            "simpleinout_list_my_statuses for their history; "
            "simpleinout_create_my_status checks the caller in/out, "
            "simpleinout_create_user_status changes someone else's status "
            "on their behalf (needs permission). simpleinout_list_roles is "
            "useful before creating/managing users since role_id is "
            "required. list_* tools accept page/page_size. Every tool "
            "except the two create_*_status tools is read-only."
        ),
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    def client_factory() -> SimpleInOutClient | None:
        return get_client_from_context(settings)

    from .tools import inout

    inout.register(mcp, client_factory)

    return mcp
