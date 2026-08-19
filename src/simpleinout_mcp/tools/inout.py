"""Simple In/Out tools: Company, Statuses, Users, Groups, Beacons, Fences,
Networks, Announcements, Roles.

Tool naming convention: simpleinout_<action>_<resource>
"""

from collections.abc import Callable
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped
from ..api_client import SimpleInOutClient, SimpleInOutError
from ._common import NO_TOKEN

# Simple In/Out's docs specify a page_size default of 25 but do not document
# any hard maximum. Use the SOP's fallback hard cap of 200 rather than
# passing an unbounded value through to the vendor API.
_MAX_PAGE_SIZE = 200

_StatusValue = Literal["in", "remote", "busy", "break", "out", "sick", "vacation"]


def _clamp_page_size(page_size: int | None) -> int | None:
    if page_size is None:
        return None
    return min(page_size, _MAX_PAGE_SIZE)


def register(mcp: FastMCP, client_factory: Callable[[], SimpleInOutClient | None]) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_get_current_company(
        expand: Annotated[
            str | None, Field(description="Comma-separated related resources to embed.")
        ] = None,
    ) -> str:
        """Get the current company's profile."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get("/companies/my", params={"expand": expand})
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_statuses(
        created_at: Annotated[
            str,
            Field(
                description=(
                    'Date/time range filter, e.g. "1523854800..1524459599" '
                    '(epoch seconds, ".." between the two values).'
                )
            ),
        ],
    ) -> str:
        """List status-change history across the whole company within a date range."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get("/statuses", params={"created_at": created_at})
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_my_statuses(
        created_at: Annotated[
            str,
            Field(
                description=(
                    'Date/time range filter, e.g. "1523854800..1524459599" '
                    '(epoch seconds, ".." between the two values).'
                )
            ),
        ],
    ) -> str:
        """List the current authenticated user's status history within a date range."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get("/users/my/statuses", params={"created_at": created_at})
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_user_statuses(
        user_id: Annotated[str, Field(description="The user's ID.")],
        created_at: Annotated[
            str,
            Field(
                description=(
                    'Date/time range filter, e.g. "1523854800..1524459599" '
                    '(epoch seconds, ".." between the two values).'
                )
            ),
        ],
    ) -> str:
        """List a specific user's status history within a date range."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(
                f"/users/{user_id}/statuses", params={"created_at": created_at}
            )
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool()
    async def simpleinout_create_my_status(
        status: Annotated[_StatusValue, Field(description="New status value.")],
        comment: Annotated[
            str | None, Field(description="Optional comment to attach to the status change.")
        ] = None,
        created_at: Annotated[
            str | None,
            Field(description="Optional timestamp to backdate/schedule the status change."),
        ] = None,
    ) -> str:
        """Create a new status entry for the current user — the core check-in/check-out action."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        payload = {"status": status, "comment": comment, "created_at": created_at}
        body = {"status": {k: v for k, v in payload.items() if v is not None}}
        try:
            result = await client.post("/users/my/statuses", body)
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool()
    async def simpleinout_create_user_status(
        user_id: Annotated[str, Field(description="The user's ID to change the status for.")],
        status: Annotated[_StatusValue, Field(description="New status value.")],
        comment: Annotated[
            str | None, Field(description="Optional comment to attach to the status change.")
        ] = None,
        created_at: Annotated[
            str | None,
            Field(description="Optional timestamp to backdate/schedule the status change."),
        ] = None,
    ) -> str:
        """Create a new status entry on behalf of another user.

        Requires the acting account to have permission to manage that user's status.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        payload = {"status": status, "comment": comment, "created_at": created_at}
        body = {"status": {k: v for k, v in payload.items() if v is not None}}
        try:
            result = await client.post(f"/users/{user_id}/statuses", body)
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_users(
        name: Annotated[str | None, Field(description="Filter by name.")] = None,
        email: Annotated[str | None, Field(description="Filter by email address.")] = None,
        group_id: Annotated[str | None, Field(description="Filter by group ID.")] = None,
        status: Annotated[str | None, Field(description="Filter by current status.")] = None,
    ) -> str:
        """List users in the company, optionally filtered."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        params = {"name": name, "email": email, "group_id": group_id, "status": status}
        try:
            result = await client.get("/users", params=params)
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_get_user(
        user_id: Annotated[str, Field(description="The user's ID.")],
    ) -> str:
        """Get a specific user by ID."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(f"/users/{user_id}")
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_get_current_user() -> str:
        """Get the current authenticated user."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get("/users/my")
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_groups(
        page: Annotated[int | None, Field(description="Page number.")] = None,
        page_size: Annotated[
            int | None, Field(description="Results per page (server default 25, max 200).")
        ] = None,
    ) -> str:
        """List groups in the company."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(
                "/groups", params={"page": page, "page_size": _clamp_page_size(page_size)}
            )
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_beacons(
        page: Annotated[int | None, Field(description="Page number.")] = None,
        page_size: Annotated[
            int | None, Field(description="Results per page (server default 25, max 200).")
        ] = None,
    ) -> str:
        """List Bluetooth presence beacons configured for the company."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(
                "/beacons", params={"page": page, "page_size": _clamp_page_size(page_size)}
            )
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_fences(
        page: Annotated[int | None, Field(description="Page number.")] = None,
        page_size: Annotated[
            int | None, Field(description="Results per page (server default 25, max 200).")
        ] = None,
    ) -> str:
        """List geofences configured for the company."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(
                "/fences", params={"page": page, "page_size": _clamp_page_size(page_size)}
            )
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_networks(
        page: Annotated[int | None, Field(description="Page number.")] = None,
        page_size: Annotated[
            int | None, Field(description="Results per page (server default 25, max 200).")
        ] = None,
    ) -> str:
        """List Wi-Fi networks used for automatic presence detection."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get(
                "/networks", params={"page": page, "page_size": _clamp_page_size(page_size)}
            )
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_announcements(
        page: Annotated[int | None, Field(description="Page number.")] = None,
        page_size: Annotated[
            int | None, Field(description="Results per page (server default 25, max 200).")
        ] = None,
        expand: Annotated[
            str | None, Field(description="Comma-separated related resources to embed.")
        ] = None,
    ) -> str:
        """List announcements for the company."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        params = {"page": page, "page_size": _clamp_page_size(page_size), "expand": expand}
        try:
            result = await client.get("/announcements", params=params)
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def simpleinout_list_roles() -> str:
        """List roles defined in the company (needed to create a user, which requires a role_id)."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.get("/roles")
            return dump_json_capped(result)
        except SimpleInOutError as e:
            return e.to_envelope()
