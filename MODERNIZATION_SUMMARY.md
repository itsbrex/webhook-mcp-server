# MCP Tool Metadata Modernization

**Date:** 2026-07-12
**SDK version:** mcp 1.28.1

## What changed

`models/schemas.py` was updated to use MCP spec features supported by the SDK:

### 1. Tool annotations (`ToolAnnotations`)

Every tool now carries behavioral hints so MCP clients can make smarter UI and safety decisions:

| Preset     | readOnly | destructive | idempotent | Used by |
|------------|----------|-------------|------------|---------|
| `_READONLY`  | true     | false       | true       | get_*, search_*, export_*, check_*, extract_* |
| `_CREATE`    | false    | false       | false      | create_webhook, create_webhook_with_config |
| `_UPDATE`    | false    | false       | true       | update_webhook |
| `_DELETE`    | false    | true        | true       | delete_webhook, delete_request, delete_all_requests |
| `_GENERATE`  | true     | false       | true       | generate_ssrf_payload, generate_xss_callback, generate_canary_token |
| `_SEND`      | false    | false       | false      | send_to_webhook, send_multiple_requests |
| `_WAIT`      | true     | false       | false      | wait_for_request, wait_for_email |

All tools set `openWorldHint=True` (they hit external webhook.site APIs) except `_GENERATE` tools which only compute payloads locally.

### 2. Human-readable titles

Every tool now has a `title` field (e.g., "Create Webhook", "Search Captured Requests") for display in MCP client UIs.

### 3. Improved descriptions

All 23 tool descriptions were rewritten to be:

- **Longer and more specific** -- explaining what the tool does, what it returns, and when to use it
- **Cross-referencing related tools** -- e.g., create_webhook mentions create_webhook_with_config, generate_ssrf_payload mentions check_for_callbacks
- **Parameter descriptions clarified** -- more context on formats, defaults, and edge cases

### 4. Tool reordering

Tools are now grouped by logical category with section comments:

1. Webhook Lifecycle (create, get info, update, delete)
2. Address Lookups (URL, email, DNS)
3. Sending Data (single, batch)
4. Reading Captured Requests (list, latest, search, export, extract links)
5. Deleting Requests (single, bulk)
6. Real-Time Waiting (request, email)
7. Security Testing / Bug Bounty (SSRF, XSS, canary, callbacks)

## What did NOT change

- Tool names (no breaking changes)
- Input schemas (same parameters, same types, same required fields)
- Handler routing (`handlers/tool_handlers.py`)
- Service layer (`services/`)
- Server entry point (`server.py`)
- No new dependencies added (`ToolAnnotations` is already in `mcp.types`)

## Verification

```
python3 -c "from models.schemas import TOOL_DEFINITIONS; print(len(TOOL_DEFINITIONS))"
# 23

python3 -c "from server import server; print('OK')"
# OK
```
