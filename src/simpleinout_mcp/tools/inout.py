"""Simple In/Out tools: Company, Statuses, Users, Groups, Beacons, Fences,
Networks, Announcements, Roles.

Tool naming convention: simpleinout_<action>_<resource>
"""

import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import SimpleInOutClient, SimpleInOutError

_NO_CREDS = (
    "Error: No Simple In/Out credentials configured. Set SIMPLEINOUT_CLIENT_ID/"
    "SIMPLEINOUT_CLIENT_SECRET/SIMPLEINOUT_REFRESH_TOKEN or use AUTH_MODE=gateway."
)


def register(mcp: FastMCP, client_factory: Callable[[], SimpleInOutClient | None]) -> None:
    @mcp.tool()
    async def simpleinout_get_current_company(expand: str | None = None) -> str:
        """Retrieve the current company.

        API: GET /companies/my

        Args:
            expand: Optional comma-separated list of related resources to embed.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/companies/my", params={"expand": expand})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_statuses(created_at: str) -> str:
        """List status-change history across the whole company within a date range.

        API: GET /statuses

        Args:
            created_at: Required. Date/time range filter, e.g. "1523854800..1524459599"
                (epoch seconds, `..` between two values for a range).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/statuses", params={"created_at": created_at})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_my_statuses(created_at: str) -> str:
        """List the current authenticated user's status history within a date range.

        API: GET /users/my/statuses

        Args:
            created_at: Required. Date/time range filter, e.g. "1523854800..1524459599".
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/users/my/statuses", params={"created_at": created_at})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_user_statuses(user_id: str, created_at: str) -> str:
        """List a specific user's status history within a date range.

        API: GET /users/:id/statuses

        Args:
            user_id: Required. The user's ID.
            created_at: Required. Date/time range filter, e.g. "1523854800..1524459599".
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get(f"/users/{user_id}/statuses", params={"created_at": created_at})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_create_my_status(
        status: str, comment: str | None = None, created_at: str | None = None
    ) -> str:
        """Create (change) the current authenticated user's status — the core
        check-in/check-out action.

        API: POST /users/my/statuses

        Args:
            status: Required. One of "in", "remote", "busy", "break", "out",
                "sick", "vacation".
            comment: Optional comment to attach to the status change.
            created_at: Optional timestamp to backdate/schedule the status change.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        payload = {"status": status, "comment": comment, "created_at": created_at}
        body = {"status": {k: v for k, v in payload.items() if v is not None}}
        try:
            result = await client.post("/users/my/statuses", body)
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_create_user_status(
        user_id: str, status: str, comment: str | None = None, created_at: str | None = None
    ) -> str:
        """Create (change) another user's status on their behalf. Requires the
        acting account to have permission to manage that user's status.

        API: POST /users/:id/statuses

        Args:
            user_id: Required. The user's ID to change the status for.
            status: Required. One of "in", "remote", "busy", "break", "out",
                "sick", "vacation".
            comment: Optional comment to attach to the status change.
            created_at: Optional timestamp to backdate/schedule the status change.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        payload = {"status": status, "comment": comment, "created_at": created_at}
        body = {"status": {k: v for k, v in payload.items() if v is not None}}
        try:
            result = await client.post(f"/users/{user_id}/statuses", body)
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_users(
        name: str | None = None,
        email: str | None = None,
        group_id: str | None = None,
        status: str | None = None,
    ) -> str:
        """List all users in the company.

        API: GET /users

        Args:
            name: Filter by name.
            email: Filter by email address.
            group_id: Filter by group ID.
            status: Filter by current status.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        params = {"name": name, "email": email, "group_id": group_id, "status": status}
        try:
            result = await client.get("/users", params=params)
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_get_user(user_id: str) -> str:
        """Retrieve a specific user.

        API: GET /users/:id

        Args:
            user_id: Required. The user's ID.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get(f"/users/{user_id}")
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_get_current_user() -> str:
        """Retrieve the current authenticated user.

        API: GET /users/my
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/users/my")
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_groups(page: int | None = None, page_size: int | None = None) -> str:
        """List all groups.

        API: GET /groups

        Args:
            page: Page number.
            page_size: Results per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/groups", params={"page": page, "page_size": page_size})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_beacons(page: int | None = None, page_size: int | None = None) -> str:
        """List all beacons (Bluetooth presence beacons).

        API: GET /beacons

        Args:
            page: Page number.
            page_size: Results per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/beacons", params={"page": page, "page_size": page_size})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_fences(page: int | None = None, page_size: int | None = None) -> str:
        """List all geofences.

        API: GET /fences

        Args:
            page: Page number.
            page_size: Results per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/fences", params={"page": page, "page_size": page_size})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_networks(page: int | None = None, page_size: int | None = None) -> str:
        """List all Wi-Fi networks used for automatic presence detection.

        API: GET /networks

        Args:
            page: Page number.
            page_size: Results per page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/networks", params={"page": page, "page_size": page_size})
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_announcements(
        page: int | None = None, page_size: int | None = None, expand: str | None = None
    ) -> str:
        """List all announcements for the company.

        API: GET /announcements

        Args:
            page: Page number.
            page_size: Results per page.
            expand: Optional comma-separated list of related resources to embed.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        params = {"page": page, "page_size": page_size, "expand": expand}
        try:
            result = await client.get("/announcements", params=params)
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def simpleinout_list_roles() -> str:
        """List all roles defined in the company (needed to create a user,
        which requires a role_id).

        API: GET /roles
        """
        client = client_factory()
        if client is None:
            return _NO_CREDS
        try:
            result = await client.get("/roles")
            return json.dumps(result, indent=2)
        except SimpleInOutError as e:
            return f"Error: {e}"
