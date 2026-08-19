"""tools/list snapshot + error-envelope mapping tests.

No network calls: tool enumeration goes through FastMCP's in-process
list_tools(), and the error-code mapping is tested directly against
SimpleInOutError, independent of any real HTTP request.
"""

import json

import pytest

from simpleinout_mcp.api_client import SimpleInOutError
from simpleinout_mcp.config import Settings
from simpleinout_mcp.server import create_mcp_server

EXPECTED_TOOLS = {
    "simpleinout_get_current_company": set(),
    "simpleinout_list_statuses": {"created_at"},
    "simpleinout_list_my_statuses": {"created_at"},
    "simpleinout_list_user_statuses": {"user_id", "created_at"},
    "simpleinout_create_my_status": {"status"},
    "simpleinout_create_user_status": {"user_id", "status"},
    "simpleinout_list_users": set(),
    "simpleinout_get_user": {"user_id"},
    "simpleinout_get_current_user": set(),
    "simpleinout_list_groups": set(),
    "simpleinout_list_beacons": set(),
    "simpleinout_list_fences": set(),
    "simpleinout_list_networks": set(),
    "simpleinout_list_announcements": set(),
    "simpleinout_list_roles": set(),
}

# The only two tools with side effects; everything else is a read-only query.
WRITE_TOOLS = {"simpleinout_create_my_status", "simpleinout_create_user_status"}


@pytest.mark.asyncio
async def test_tools_list_snapshot():
    mcp = create_mcp_server(Settings())
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == set(EXPECTED_TOOLS), f"unexpected tool set: {names}"

    by_name = {t.name: t for t in tools}
    for name, expected_required in EXPECTED_TOOLS.items():
        tool = by_name[name]
        required = set(tool.inputSchema.get("required", []))
        assert required == expected_required, f"{name}: required={required}"

        if name in WRITE_TOOLS:
            assert tool.annotations is None or tool.annotations.readOnlyHint is not True
        else:
            assert tool.annotations is not None and tool.annotations.readOnlyHint is True

        assert len(tool.description or "") <= 500, f"{name}: description too long"
        first_line = (tool.description or "").strip().splitlines()[0]
        assert len(first_line) <= 100, f"{name}: first line too long: {first_line!r}"
        assert "API:" not in (tool.description or ""), f"{name}: leaks implementation detail"


@pytest.mark.asyncio
async def test_service_instructions_present_and_bounded():
    mcp = create_mcp_server(Settings())
    assert mcp.instructions
    assert len(mcp.instructions) <= 1500


@pytest.mark.parametrize(
    "status_code,expected_code,expected_retryable",
    [
        (0, "upstream_error", True),
        (400, "invalid_argument", False),
        (401, "unauthorized", False),
        (403, "unauthorized", False),
        (404, "not_found", False),
        (422, "invalid_argument", False),
        (429, "rate_limited", True),
        (500, "upstream_error", True),
        (503, "upstream_error", True),
    ],
)
def test_error_envelope_mapping(status_code, expected_code, expected_retryable):
    err = SimpleInOutError(status_code, "boom")
    envelope = json.loads(err.to_envelope())
    assert envelope["error"]["code"] == expected_code
    assert envelope["error"]["retryable"] is expected_retryable
    assert envelope["error"]["message"] == "boom"
