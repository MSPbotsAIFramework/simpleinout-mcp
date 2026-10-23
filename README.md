# simpleinout-mcp

Simple In/Out MCP Service — a stateless HTTP MCP server wrapping the [Simple In/Out APIv4](https://www.simpleinout.com/api/docs), covering company info, in/out statuses, users, groups, beacons, geofences, networks, announcements, and roles.

**Tech stack:** Python 3.12 + uv + FastMCP (Starlette/Uvicorn)

It follows the MSPbots **Vendor MCP Service SOP**: stateless, no stored credentials, per-request header authentication only (no environment-variable credential fallback on the HTTP path).

<div align="center">

## MSPbots Connector

**The MCP Gateway built for MSPs: visible, controlled, and your data stays where it belongs.**

[**Get started at connect.mspbots.ai →**](https://connect.mspbots.ai)

</div>

---

MSPbots Connector gives your AI clients one MCP URL to reach your entire MSP stack (RMM, PSA, documentation, security, finance), and gives you control over who can call which tool and a record of everything that was called.

**Hosted service: [connect.mspbots.ai](https://connect.mspbots.ai)** · Free to use.

### Why Connector

![MSPbots Connector](https://stgoss.mspbots.ai/files/mcp/mspbots-mcp.png)

| | |
|---|---|
| **Visible** | Every tool call is logged: who, which vendor, when. Usage dashboard, CSV export, SIEM streaming. |
| **Controlled** | Role-based, per-tool allowlist. Deny by default. |
| **Protected** | Credentials encrypted per record. AI clients never see your vendor passwords or tokens. |
| **MSP-native** | Built for the MSP stack only: RMM, PSA, documentation, security, finance. |

### Quick start

1. **Sign up** at [connect.mspbots.ai](https://connect.mspbots.ai).
2. **Connect your vendors.** Pick from 150+ connectors and authorize each one on the vendor's own page, or bring your own API keys. No extra vendor accounts needed.
3. **Set access.** Create roles and decide which tools each role may call. Nothing is allowed until you allow it.
4. **Add your MCP URL to your AI client.** Copy the URL from your Connector dashboard into Claude, ChatGPT, Cursor, VS Code, Gemini, Codex, or any MCP-capable client.
5. **Ask your AI to do real work**, and watch every call appear in the audit log.

### Features

**Unified gateway**
- One MCP URL for all your AI clients
- 150+ connectors across the MSP stack
- Custom MCP servers supported, free
- Authorization happens on each vendor's own page; the AI never sees passwords or tokens
- Bring your own credentials: use the vendor API keys you already have
- Multiple accounts per app; connect once, reuse across AI clients
- Tool search: finds the right action for the task
- One sign-in; vendor credentials are injected behind the scenes and OAuth tokens refresh automatically

**Visibility**
- Audit log for every tool call (who, which vendor, when)
- Usage dashboard: call volume, top vendors, error rate, per-user activity
- Export audit logs to CSV, or stream to Loki, Graylog, or LogScale (SIEM)
- Optional recording of tool arguments and result summaries (off by default, enabled per organization)

**Control**
- Per-role, per-tool allowlist, deny by default
- owner / admin / member roles
- SCIM provisioning with Entra ID, Okta, JumpCloud, and Google Workspace

**Security**
- Credentials encrypted one record at a time (AES-256-GCM, per-record key)
- AI clients authenticate with OAuth 2.1 + PKCE
- Vendor responses are scanned for prompt-injection patterns and returned as structured data. This is one layer of defense, not a guarantee against every attack.
- Static egress IP for customer firewall and API allowlisting

### Pricing

**Free.**

Links: [connect.mspbots.ai](https://connect.mspbots.ai) · [mspbots.ai](https://mspbots.ai)

---

## Scope

**15 tools**, going beyond MSPbots' historical usage (which was just 1 endpoint — "Companies") to cover the broader resource catalog, prioritizing the core check-in/check-out status feature plus the read-side of every other resource category the API exposes.

## Authentication

Simple In/Out's API is **pure OAuth2 with no non-redirect alternative** (confirmed against the official docs — only `authorization_code` and `refresh_token` grants exist; no `client_credentials`, no API key). However, **the redirect step is only needed once, by a human, out-of-band** — not by this service at runtime:

1. **One-time setup (a person does this, not the MCP):** visit `GET /oauth/authorize?response_type=code&client_id=...&redirect_uri=...&scope=write`, log in, approve. Exchange the returned `code` for an `access_token` + `refresh_token` via `POST /oauth/token` with `grant_type=authorization_code`.
2. **Ongoing operation (this service does this, per call):** exchange the `refresh_token` for a fresh `access_token` via `POST /oauth/token` with `grant_type=refresh_token` — this grant needs only `client_id` + `client_secret` + `refresh_token`, **no redirect_uri**. Since access tokens are cheap to re-mint and this service must stay stateless, it does this on every call rather than caching (no cross-request caching of tokens either — see SOP §3.4).

So the only credentials this service needs are `client_id`, `client_secret`, and a `refresh_token` obtained once via step 1. **These values are supplied per-request via HTTP headers only** — there is no environment variable or config field for them, and no fallback that would read them from the environment.

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
```

The server starts on `http://localhost:8080`.

### Local (uv)

```bash
uv sync
python -m simpleinout_mcp
```

## Health Check

```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

No credentials are required for the health endpoint (it is a pure local liveness probe and does not call the Simple In/Out API).

## HEADER Authorization Parameters (Authentication)

Every request to `/mcp` must include all three of the following HTTP headers:

| Header | Type | Required | Default | Allowed values | Description | Example |
|---|---|---|---|---|---|---|
| `X-SimpleInOut-Client-Id` | string | Yes | None | None | Simple In/Out OAuth2 client ID (request it by emailing help@simplymadeapps.com) | `abc123def456` |
| `X-SimpleInOut-Client-Secret` | string | Yes | None | None | Simple In/Out OAuth2 client secret | `xyz789uvw012` |
| `X-SimpleInOut-Refresh-Token` | string | Yes | None | None | refresh_token obtained from a one-time manual login authorization (this service uses it on every call to obtain a new access_token; no redirect_uri is needed) | `osm5x33j2wd6rlsnwenrdrlgk1jpgsi5` |

Missing any of the three headers returns `401 Unauthorized` with the list of required header names in the response body.

## Environment Variables

Non-credential configuration only — see Authentication above for how credentials are supplied.

| Variable | Default | Description |
|----------|---------|--------------|
| `MCP_HTTP_PORT` | `8080` | HTTP server listening port |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP server listening host |
| `SIMPLEINOUT_CLIENT_ID_HEADER` | `X-SimpleInOut-Client-Id` | Header name the Gateway sends the client ID under (name only, not a credential value) |
| `SIMPLEINOUT_CLIENT_SECRET_HEADER` | `X-SimpleInOut-Client-Secret` | Header name for the client secret |
| `SIMPLEINOUT_REFRESH_TOKEN_HEADER` | `X-SimpleInOut-Refresh-Token` | Header name for the refresh token |

## MCP Endpoint

```
POST http://localhost:8080/mcp
```

Connect your MCP client with:
- Transport: `http` (Streamable HTTP)
- Headers: `X-SimpleInOut-Client-Id`, `X-SimpleInOut-Client-Secret`, `X-SimpleInOut-Refresh-Token` (all required)

## Available Tools (15)

| Tool | Description | Simple In/Out endpoint |
|---|---|---|
| `simpleinout_get_current_company` | Get the current company's profile | `GET /companies/my` |
| `simpleinout_list_statuses` | List status-change history company-wide | `GET /statuses` |
| `simpleinout_list_my_statuses` | List the current user's status history | `GET /users/my/statuses` |
| `simpleinout_list_user_statuses` | List a specific user's status history | `GET /users/:id/statuses` |
| `simpleinout_create_my_status` | Create a new status for the current user (check in/out) | `POST /users/my/statuses` |
| `simpleinout_create_user_status` | Create a new status for another user | `POST /users/:id/statuses` |
| `simpleinout_list_users` | List all users, optionally filtered | `GET /users` |
| `simpleinout_get_user` | Get a specific user | `GET /users/:id` |
| `simpleinout_get_current_user` | Get the current authenticated user | `GET /users/my` |
| `simpleinout_list_groups` | List all groups | `GET /groups` |
| `simpleinout_list_beacons` | List all beacons | `GET /beacons` |
| `simpleinout_list_fences` | List all geofences | `GET /fences` |
| `simpleinout_list_networks` | List all Wi-Fi networks | `GET /networks` |
| `simpleinout_list_announcements` | List all announcements | `GET /announcements` |
| `simpleinout_list_roles` | List all roles | `GET /roles` |

All tools are read-only except `simpleinout_create_my_status` and `simpleinout_create_user_status`. `page_size` on the `list_groups`/`list_beacons`/`list_fences`/`list_networks`/`list_announcements` tools is clamped server-side to 200 (Simple In/Out's docs specify a default of 25 but do not document a hard maximum, so the SOP's fallback ceiling is used).

## Test Example

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-SimpleInOut-Client-Id: <client_id>" \
  -H "X-SimpleInOut-Client-Secret: <client_secret>" \
  -H "X-SimpleInOut-Refresh-Token: <refresh_token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": { "name": "simpleinout_get_current_user", "arguments": {} }
  }'
```

Per SOP §12, run `initialize` → `tools/list` → `tools/call` in that order with your own test credentials before considering the service verified end-to-end — `/health` returning 200 does not imply `/mcp` is usable.

## Known Gaps

- **⚠️ Not yet tested against a live Simple In/Out account.** All 15 tools checked structurally only (MCP handshake, tools-list, schema validity, `/health`, gateway 401 credential-gating). Per the parent ClickUp task, the previously-applied API client has expired; a new one has been requested via email (registering MSPbots' own MCP Management Service OAuth callback URLs as the redirect URIs) and is pending Simple In/Out's reply. Once a client_id/secret comes back, someone still needs to do the one-time interactive authorization to obtain the initial refresh_token before this can be tested end-to-end.
- Endpoint paths/params verified directly against the docs' verbatim `Endpoint`/`Route`/`Parameters` blocks (page text extraction, not an AI-summarized fetch) — not guessed.
- **"Settings" has no documented endpoint at all** — it only appears as a timestamp key inside the `meta.last_updated_at` object on every response, not as its own resource. Not built as a tool.
- **"Favorites" is not a top-level resource** — all favorites actions live under `/users/my/favorites` (bulk-replace via `POST`) and `/users/my/statuses/favorite`/`/hide`/`/unfavorite` (per-item). No `GET /favorites` exists. Not built as a tool in this 15-tool scope; the `POST /users/my/favorites` bulk-replace endpoint could be added if favorites management is needed.
- Statuses have no update/PATCH — a status is an immutable log entry; "changing" status means creating a new one (`simpleinout_create_my_status`/`simpleinout_create_user_status`).
- Scope is limited to the 15 operations above, not the full API surface (which also includes user/role/group create-update-delete, beacon/fence/network create-update-delete, and the newer Reporting API endpoint mentioned in Simple In/Out's changelog).
- `simpleinout_list_users` has no documented pagination parameters in the vendor docs (unlike groups/beacons/fences/networks/announcements), so no `page`/`page_size` args were added to it.

## API Reference

- [Simple In/Out API v4 Documentation](https://www.simpleinout.com/api/docs)
- [How to request API credentials](https://simpleinout.helpscoutdocs.com/article/126-api) (email `help@simplymadeapps.com`, subject "API")
