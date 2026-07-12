# Dependency Audit — 2026-07-12

## Security Scan

**Tool:** `pip-audit` (v2.10.1) against installed site-packages

**Result:** No known vulnerabilities found. Zero CVEs in any direct or transitive dependency.

## Installed Versions vs Latest (all current)

| Package | Installed | Latest | Notes |
|---|---|---|---|
| mcp | 1.28.1 | 1.28.1 | v2.0.0 releasing 2026-07-28 — breaking |
| httpx | 0.28.1 | 0.28.1 | |
| pytest | 9.1.1 | 9.1.1 | |
| pytest-asyncio | 1.4.0 | 1.4.0 | |
| pydantic | 2.13.4 | 2.13.4 | transitive via mcp |
| starlette | 1.3.1 | 1.3.1 | transitive via mcp |
| uvicorn | 0.51.0 | 0.51.0 | transitive via mcp |
| anyio | 4.14.1 | 4.14.1 | |
| httpcore | 1.0.9 | 1.0.9 | |
| httpx-sse | 0.4.3 | 0.4.3 | |
| sse-starlette | 3.4.5 | 3.4.5 | |
| hatchling | 1.31.0 | 1.31.0 | build dep |
| aiohttp | 3.14.1 | 3.14.1 | test dep (was missing from pyproject.toml) |

## Changes to pyproject.toml

### `mcp>=1.0.0` → `mcp>=1.28.0,<2`

The `<2` upper bound is critical. MCP v2.0.0 ships 2026-07-28 alongside the new
MCP 2026-07-28 spec. It has breaking changes: the session-centric v1 internals
are replaced by a dispatcher/runner pipeline, `FastMCP` is renamed to
`MCPServer`, and the types package is split out to `mcp-types`. Without the
upper bound, `uv sync` on or after July 28 would pull v2 and break the server.

### `httpx>=0.25.0` → `httpx>=0.28.0`

Tightened floor to current major release line.

### `pytest>=8.0.0` → `pytest>=9.0.0`

Tightened floor to current major release line.

### `pytest-asyncio>=1.0.0` → `pytest-asyncio>=1.4.0`

Tightened floor to current stable.

### `hatchling` (unpinned) → `hatchling>=1.31.0`

Added minimum version pin for the build backend.

### Added `aiohttp>=3.14.0` to `[dev]`

Tests import `aiohttp` but it was missing from the dev dependencies.

## Verification

- All deps install cleanly with `pip install -e ".[dev]"` on Python 3.10
- `server.run_server` imports without error
- 31 of 32 tests pass; the one failure (`test_get_all_requests`) is a
  pre-existing timing issue in a live integration test (asserts `>= 3`
  requests but only 2 arrived), unrelated to dependency changes

## Action Item

Before 2026-07-28, review the MCP v2.0.0 migration guide and plan the upgrade.
The `<2` pin buys time but the project should migrate to v2 to stay supported.
