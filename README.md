# simpleinout-mcp

Simple In/Out MCP Service — a stateless HTTP MCP server wrapping the [Simple In/Out APIv4](https://www.simpleinout.com/api/docs), covering company info, in/out statuses, users, groups, beacons, geofences, networks, announcements, and roles.

**Tech stack:** Python 3.12 + uv + FastMCP (Starlette/Uvicorn)

## Scope

**15 tools**, going beyond MSPbots' historical usage (which was just 1 endpoint — "Companies") to cover the broader resource catalog, prioritizing the core check-in/check-out status feature plus the read-side of every other resource category the API exposes.

## Authentication

Simple In/Out's API is **pure OAuth2 with no non-redirect alternative** (confirmed against the official docs — only `authorization_code` and `refresh_token` grants exist; no `client_credentials`, no API key). However, **the redirect step is only needed once, by a human, out-of-band** — not by this service at runtime:

1. **One-time setup (a person does this, not the MCP):** visit `GET /oauth/authorize?response_type=code&client_id=...&redirect_uri=...&scope=write`, log in, approve. Exchange the returned `code` for an `access_token` + `refresh_token` via `POST /oauth/token` with `grant_type=authorization_code`.
2. **Ongoing operation (this service does this, per call):** exchange the `refresh_token` for a fresh `access_token` via `POST /oauth/token` with `grant_type=refresh_token` — this grant needs only `client_id` + `client_secret` + `refresh_token`, **no redirect_uri**. Since access tokens are cheap to re-mint and this service must stay stateless, it does this on every call rather than caching.

So the only credentials this service needs are `client_id`, `client_secret`, and a `refresh_token` obtained once via step 1.

## Quick Start

```powershell
cd D:\claude\project\simpleinout-mcp
uv sync

$env:SIMPLEINOUT_CLIENT_ID="your_client_id"
$env:SIMPLEINOUT_CLIENT_SECRET="your_client_secret"
$env:SIMPLEINOUT_REFRESH_TOKEN="your_refresh_token"
uv run simpleinout-mcp
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Description |
|----------|---------|--------------|
| `SIMPLEINOUT_CLIENT_ID` | — | Simple In/Out OAuth2 client ID |
| `SIMPLEINOUT_CLIENT_SECRET` | — | Simple In/Out OAuth2 client secret |
| `SIMPLEINOUT_REFRESH_TOKEN` | — | Refresh token obtained from the one-time interactive authorization (see above) |
| `AUTH_MODE` | `gateway` | `gateway` = credentials per-request via headers (SOP-compliant); `env` = shared credentials from env vars (local dev only) |
| `MCP_TRANSPORT` | `stdio` | `stdio` (Claude Desktop) or `http` (gateway) |
| `MCP_HTTP_PORT` | `8080` | HTTP server port |

## HEADER 授权参数说明

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `X-SimpleInOut-Client-Id` | string | 是 | 无 | 无 | Simple In/Out OAuth2 client ID（发邮件到 help@simplymadeapps.com 申请） | `abc123def456` |
| `X-SimpleInOut-Client-Secret` | string | 是 | 无 | 无 | Simple In/Out OAuth2 client secret | `xyz789uvw012` |
| `X-SimpleInOut-Refresh-Token` | string | 是 | 无 | 无 | 一次性人工登录授权换出来的 refresh_token（本服务用它每次调用换新的 access_token，不需要 redirect_uri） | `osm5x33j2wd6rlsnwenrdrlgk1jpgsi5` |

## Claude Desktop Setup

```json
{
  "mcpServers": {
    "simpleinout": {
      "command": "uv",
      "args": ["run", "--directory", "D:/claude/project/simpleinout-mcp", "simpleinout-mcp"],
      "env": {
        "SIMPLEINOUT_CLIENT_ID": "your_client_id",
        "SIMPLEINOUT_CLIENT_SECRET": "your_client_secret",
        "SIMPLEINOUT_REFRESH_TOKEN": "your_refresh_token"
      }
    }
  }
}
```

## Transport Modes

### stdio
```powershell
$env:SIMPLEINOUT_CLIENT_ID="your_client_id"
$env:SIMPLEINOUT_CLIENT_SECRET="your_client_secret"
$env:SIMPLEINOUT_REFRESH_TOKEN="your_refresh_token"
uv run simpleinout-mcp
```

### HTTP — single-tenant
```powershell
$env:SIMPLEINOUT_CLIENT_ID="your_client_id"
$env:SIMPLEINOUT_CLIENT_SECRET="your_client_secret"
$env:SIMPLEINOUT_REFRESH_TOKEN="your_refresh_token"
$env:MCP_TRANSPORT="http"
$env:AUTH_MODE="env"
uv run simpleinout-mcp
```

### HTTP — gateway / multi-tenant
```powershell
$env:MCP_TRANSPORT="http"
$env:AUTH_MODE="gateway"
uv run simpleinout-mcp
# Each request must include: X-SimpleInOut-Client-Id, X-SimpleInOut-Client-Secret, X-SimpleInOut-Refresh-Token headers
```

## Available Tools (15)

| Tool | Description | API |
|---|---|---|
| `simpleinout_get_current_company` | Retrieve the current company | `GET /companies/my` |
| `simpleinout_list_statuses` | List status-change history company-wide | `GET /statuses` |
| `simpleinout_list_my_statuses` | List the current user's status history | `GET /users/my/statuses` |
| `simpleinout_list_user_statuses` | List a specific user's status history | `GET /users/:id/statuses` |
| `simpleinout_create_my_status` | Change the current user's status (check in/out) | `POST /users/my/statuses` |
| `simpleinout_create_user_status` | Change another user's status | `POST /users/:id/statuses` |
| `simpleinout_list_users` | List all users | `GET /users` |
| `simpleinout_get_user` | Retrieve a specific user | `GET /users/:id` |
| `simpleinout_get_current_user` | Retrieve the current authenticated user | `GET /users/my` |
| `simpleinout_list_groups` | List all groups | `GET /groups` |
| `simpleinout_list_beacons` | List all beacons | `GET /beacons` |
| `simpleinout_list_fences` | List all geofences | `GET /fences` |
| `simpleinout_list_networks` | List all Wi-Fi networks | `GET /networks` |
| `simpleinout_list_announcements` | List all announcements | `GET /announcements` |
| `simpleinout_list_roles` | List all roles | `GET /roles` |

## Known Gaps

- **⚠️ Not yet tested against a live Simple In/Out account.** All 15 tools checked structurally only (MCP handshake, tools-list, schema validity, `/health`, gateway 401 credential-gating). Per the parent ClickUp task, the previously-applied API client has expired; a new one has been requested via email (registering MSPbots' own MCP Management Service OAuth callback URLs as the redirect URIs) and is pending Simple In/Out's reply. Once a client_id/secret comes back, someone still needs to do the one-time interactive authorization to obtain the initial refresh_token before this can be tested end-to-end.
- Endpoint paths/params verified directly against the docs' verbatim `Endpoint`/`Route`/`Parameters` blocks (page text extraction, not an AI-summarized fetch) — not guessed.
- **"Settings" has no documented endpoint at all** — it only appears as a timestamp key inside the `meta.last_updated_at` object on every response, not as its own resource. Not built as a tool.
- **"Favorites" is not a top-level resource** — all favorites actions live under `/users/my/favorites` (bulk-replace via `POST`) and `/users/my/statuses/favorite`/`/hide`/`/unfavorite` (per-item). No `GET /favorites` exists. Not built as a tool in this 15-tool scope; the `POST /users/my/favorites` bulk-replace endpoint could be added if favorites management is needed.
- Statuses have no update/PATCH — a status is an immutable log entry; "changing" status means creating a new one (`simpleinout_create_my_status`/`simpleinout_create_user_status`).
- Scope is limited to the 15 operations above, not the full API surface (which also includes user/role/group create-update-delete, beacon/fence/network create-update-delete, and the newer Reporting API endpoint mentioned in Simple In/Out's changelog).

## API Reference

- [Simple In/Out API v4 Documentation](https://www.simpleinout.com/api/docs)
- [How to request API credentials](https://simpleinout.helpscoutdocs.com/article/126-api) (email `help@simplymadeapps.com`, subject "API")
