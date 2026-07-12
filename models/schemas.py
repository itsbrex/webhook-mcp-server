"""
Data models and MCP tool schemas for the webhook.site MCP server.

This module contains:
- Dataclasses for structured data (WebhookConfig, SearchFilters, etc.)
- MCP Tool definitions with input schemas
- Response models for consistent API responses
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any
from mcp.types import Tool, ToolAnnotations


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class WebhookConfig:
    """Configuration for creating/updating a webhook.
    
    Args:
        default_status: HTTP status code for responses (200-599)
        default_content: Response body content
        default_content_type: Content-Type header value
        timeout: Seconds to wait before responding (0-30)
        cors: Enable CORS headers
        alias: Custom URL alias (3-32 alphanumeric chars)
        expiry: Seconds until auto-expiration (max 604800)
    """
    default_status: int | None = None
    default_content: str | None = None
    default_content_type: str | None = None
    timeout: int | None = None
    cors: bool | None = None
    alias: str | None = None
    expiry: int | None = None
    listen: int | None = None
    request_limit: int | None = None
    actions: bool | None = None
    clone_from: str | None = None
    group_id: int | None = None

    def to_payload(self) -> dict[str, Any]:
        """Convert to API payload, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SearchFilters:
    """Filters for searching webhook requests.
    
    Args:
        request_type: Filter by type ('web', 'email', 'dns')
        query: Additional search query string (e.g., 'method:POST', 'content:hello')
        date_from: Start date filter (format: yyyy-MM-dd HH:mm:ss)
        date_to: End date filter (format: yyyy-MM-dd HH:mm:ss)
        sorting: Sort order ('newest' or 'oldest')
        limit: Maximum results to return
    """
    request_type: str | None = None
    query: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    sorting: str = "newest"
    limit: int = 20
    
    def to_params(self) -> dict[str, Any]:
        """Convert to query parameters."""
        params = {"per_page": self.limit, "sorting": self.sorting}
        
        # Build query string with type filter if specified
        query_parts = []
        if self.request_type:
            query_parts.append(f"type:{self.request_type}")
        if self.query:
            query_parts.append(self.query)
        if query_parts:
            params["query"] = " ".join(query_parts)
        
        if self.date_from:
            params["date_from"] = self.date_from
        if self.date_to:
            params["date_to"] = self.date_to
        return params


@dataclass
class DeleteFilters:
    """Filters for bulk deleting requests.
    
    Args:
        date_from: Delete from date (format: yyyy-MM-dd HH:mm:ss or 'now-7d')
        date_to: Delete until date (format: yyyy-MM-dd HH:mm:ss or 'now-7d')
        query: Delete only matching requests
    """
    date_from: str | None = None
    date_to: str | None = None
    query: str | None = None
    
    def to_params(self) -> dict[str, str]:
        """Convert to query parameters."""
        params = {}
        if self.date_from:
            params["date_from"] = self.date_from
        if self.date_to:
            params["date_to"] = self.date_to
        if self.query:
            params["query"] = self.query
        return params


@dataclass
class ToolResult:
    """Standardized result from a tool operation.
    
    Args:
        success: Whether the operation succeeded
        message: Human-readable result message
        data: Additional result data
    """
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        result = {"success": self.success, "message": self.message}
        result.update(self.data)
        return json.dumps(result, indent=2)


# =============================================================================
# TOOL ANNOTATION PRESETS
# =============================================================================

_READONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_CREATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)

_UPDATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_DELETE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=True,
)

_GENERATE = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

_SEND = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)

_WAIT = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

TOOL_DEFINITIONS: list[Tool] = [
    # =========================================================================
    # WEBHOOK LIFECYCLE
    # =========================================================================
    Tool(
        name="create_webhook",
        title="Create Webhook",
        description=(
            "Create a new webhook.site endpoint with default settings. "
            "Returns a unique UUID token and the full URL (https://webhook.site/{token}) "
            "where incoming HTTP requests, emails, and DNS lookups will be captured. "
            "Use this when you need a quick, disposable endpoint for testing callbacks, "
            "OAuth flows, or API integrations. For custom response behavior, use "
            "create_webhook_with_config instead."
        ),
        annotations=_CREATE,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="create_webhook_with_config",
        title="Create Webhook with Configuration",
        description=(
            "Create a new webhook.site endpoint with custom configuration. "
            "Allows you to set the HTTP response status code, body, content type, "
            "response delay, CORS headers, a custom URL alias, and auto-expiration. "
            "Returns the UUID token and full URL. Use this when the webhook must return "
            "specific responses (e.g., mock API, redirect, or error simulation) or when "
            "you need a human-readable alias instead of a UUID."
        ),
        annotations=_CREATE,
        inputSchema={
            "type": "object",
            "properties": {
                "default_status": {
                    "type": "integer",
                    "description": "HTTP status code the webhook returns to callers (200-599). Default: 200.",
                    "default": 200,
                },
                "default_content": {
                    "type": "string",
                    "description": "Response body the webhook returns to callers. Default: empty.",
                    "default": "",
                },
                "default_content_type": {
                    "type": "string",
                    "description": "Content-Type header on the webhook's response. Default: text/html.",
                    "default": "text/html",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Seconds the webhook waits before responding (0-30). Useful for simulating slow APIs.",
                    "default": 0,
                },
                "cors": {
                    "type": "boolean",
                    "description": "When true, the webhook adds CORS headers so browser-based JavaScript can call it.",
                    "default": False,
                },
                "alias": {
                    "type": "string",
                    "description": "Custom URL slug (3-32 alphanumeric chars). The webhook becomes https://webhook.site/{alias}.",
                },
                "expiry": {
                    "type": "integer",
                    "description": "Auto-delete the webhook after this many seconds (max 604800 = 7 days).",
                },
                "listen": {
                    "type": "integer",
                    "description": "Response listening timeout in seconds (0-10). When set, the webhook waits for a programmatic response via the API before replying to the caller.",
                },
                "request_limit": {
                    "type": "integer",
                    "description": "Maximum number of requests to keep in history (0-10000). Older requests are discarded when the limit is reached.",
                },
                "actions": {
                    "type": "boolean",
                    "description": "When true, enables Custom Actions on this webhook so server-side automation rules can fire on incoming requests.",
                },
                "clone_from": {
                    "type": "string",
                    "description": "UUID of an existing webhook token whose settings, Custom Actions, and response config should be cloned into this new webhook.",
                },
                "group_id": {
                    "type": "integer",
                    "description": "Numeric ID of the group to assign this webhook to. Groups organize webhooks in the dashboard.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_webhook_info",
        title="Get Webhook Details",
        description=(
            "Retrieve the full configuration and metadata for an existing webhook. "
            "Returns settings (status code, content type, CORS, timeout), creation date, "
            "expiration date, request count, and the associated URL/email/DNS addresses. "
            "Use this to inspect or audit a webhook before modifying it."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token identifying the webhook on webhook.site.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="update_webhook",
        title="Update Webhook Settings",
        description=(
            "Modify the response behavior of an existing webhook. "
            "You can change the HTTP status code, response body, content type, "
            "response delay, and CORS setting. Only the fields you provide are updated; "
            "omitted fields keep their current values. "
            "Use this to change what callers receive without creating a new endpoint."
        ),
        annotations=_UPDATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token identifying the webhook to update.",
                },
                "default_status": {
                    "type": "integer",
                    "description": "New HTTP status code the webhook returns (200-599).",
                },
                "default_content": {
                    "type": "string",
                    "description": "New response body content.",
                },
                "default_content_type": {
                    "type": "string",
                    "description": "New Content-Type header value.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "New response delay in seconds (0-30).",
                },
                "cors": {
                    "type": "boolean",
                    "description": "Enable or disable CORS headers.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="delete_webhook",
        title="Delete Webhook",
        description=(
            "Permanently delete a webhook.site endpoint and all captured requests, "
            "emails, and DNS lookups associated with it. This action is irreversible. "
            "The webhook URL will stop accepting traffic immediately."
        ),
        annotations=_DELETE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to permanently delete.",
                },
            },
            "required": ["webhook_token"],
        },
    ),

    Tool(
        name="list_tokens",
        title="List All Webhooks",
        description=(
            "List all webhook tokens owned by the authenticated user. "
            "Returns an array of token objects with their UUIDs, aliases, creation dates, "
            "request counts, and configuration. Requires an API key. "
            "Use this to inventory your active webhooks or find a specific token by alias."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),

    # =========================================================================
    # ADDRESS LOOKUPS
    # =========================================================================
    Tool(
        name="get_webhook_url",
        title="Get Webhook URL",
        description=(
            "Return the full HTTP URL for a webhook token "
            "(https://webhook.site/{token}). Optionally validates that the token "
            "exists on the server before returning. Use this to quickly construct "
            "the URL you need to share or inject into a system under test."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token identifying the webhook.",
                },
                "validate": {
                    "type": "boolean",
                    "description": "When true, makes an API call to confirm the token exists before returning the URL.",
                    "default": False,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="get_webhook_email",
        title="Get Webhook Email Address",
        description=(
            "Return the unique email address for a webhook token "
            "({token}@email.webhook.site). Emails sent to this address are captured "
            "as requests on the webhook, complete with headers, body, and attachments. "
            "Use this for testing email-triggered workflows, magic-link auth flows, "
            "or email verification. Optionally validates the token first."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token identifying the webhook.",
                },
                "validate": {
                    "type": "boolean",
                    "description": "When true, confirms the token exists before returning the email address.",
                    "default": False,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="get_webhook_dns",
        title="Get Webhook DNS Domain",
        description=(
            "Return the unique DNSHook domain for a webhook token "
            "({token}.dnshook.site). Any DNS lookup against this domain or its "
            "subdomains is captured as a request on the webhook. "
            "Use this for out-of-band DNS exfiltration testing, canary tokens, or "
            "detecting blind SSRF in targets that block HTTP but allow DNS. "
            "Optionally validates the token first."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token identifying the webhook.",
                },
                "validate": {
                    "type": "boolean",
                    "description": "When true, confirms the token exists before returning the DNS domain.",
                    "default": False,
                },
            },
            "required": ["webhook_token"],
        },
    ),

    # =========================================================================
    # SENDING DATA
    # =========================================================================
    Tool(
        name="send_to_webhook",
        title="Send Request to Webhook",
        description=(
            "Send a POST request with a JSON body to a webhook.site endpoint. "
            "The request is captured and can be retrieved later with get_webhook_requests. "
            "Use this to simulate incoming webhooks, test payload handling, or push "
            "test data to an endpoint. Custom headers can be included to test "
            "header-based routing or authentication."
        ),
        annotations=_SEND,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the target webhook.",
                },
                "data": {
                    "type": "object",
                    "description": "JSON object to send as the POST body.",
                },
                "headers": {
                    "type": "object",
                    "description": "Additional HTTP headers to include (e.g., Authorization, X-Custom-Header).",
                    "default": {},
                },
            },
            "required": ["webhook_token", "data"],
        },
    ),
    Tool(
        name="send_multiple_requests",
        title="Send Batch Requests",
        description=(
            "Send multiple POST requests to a webhook in a single operation. "
            "Each payload in the array is sent as a separate HTTP request. "
            "An optional delay between requests prevents rate-limiting. "
            "Returns a summary with success/failure counts. "
            "Use this for load testing, sending a set of test payloads, or "
            "simulating a burst of webhook events."
        ),
        annotations=_SEND,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the target webhook.",
                },
                "payloads": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of JSON objects; each is sent as a separate POST request.",
                },
                "delay_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait between sending each request. Default: 0 (no delay).",
                    "default": 0,
                },
            },
            "required": ["webhook_token", "payloads"],
        },
    ),

    # =========================================================================
    # READING CAPTURED REQUESTS
    # =========================================================================
    Tool(
        name="get_webhook_requests",
        title="List Captured Requests",
        description=(
            "Retrieve captured requests (HTTP, email, or DNS) for a webhook, "
            "ordered by most recent first. Each request includes method, URL, headers, "
            "body, source IP, timestamp, and size. "
            "Use this to inspect what traffic a webhook has received. "
            "For more targeted lookups, use search_requests instead."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to query.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of requests to return. Default: 10.",
                    "default": 10,
                },
                "request_type": {
                    "type": "string",
                    "description": "Restrict results to this type: 'web' (HTTP), 'email', or 'dns'.",
                    "enum": ["web", "email", "dns"],
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="get_latest_request",
        title="Get Latest Request",
        description=(
            "Retrieve the single most recent request captured by a webhook. "
            "Returns full details: method, URL, headers, body, source IP, and timestamp. "
            "Use this for a quick check after triggering a callback or sending a test request."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to query.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="search_requests",
        title="Search Captured Requests",
        description=(
            "Search and filter captured requests using a query DSL. "
            "Supports filtering by HTTP method (method:POST), body content "
            "(content:foobar), headers (headers.user-agent:Mozilla), request type "
            "(web/email/dns), date range, and sort order. "
            "Returns matching requests with full details. "
            "Use this when you need to find specific requests among many captured ones."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to search.",
                },
                "request_type": {
                    "type": "string",
                    "description": "Restrict to 'web' (HTTP), 'email', or 'dns' requests.",
                    "enum": ["web", "email", "dns"],
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Search query using webhook.site DSL. Examples: "
                        "'method:POST', 'content:foobar', 'headers.user-agent:Mozilla'."
                    ),
                },
                "date_from": {
                    "type": "string",
                    "description": "Include only requests after this datetime (yyyy-MM-dd HH:mm:ss).",
                },
                "date_to": {
                    "type": "string",
                    "description": "Include only requests before this datetime (yyyy-MM-dd HH:mm:ss).",
                },
                "sorting": {
                    "type": "string",
                    "description": "Sort order: 'newest' (default) or 'oldest'.",
                    "default": "newest",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return. Default: 20.",
                    "default": 20,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="export_webhook_data",
        title="Export Webhook Data",
        description=(
            "Export all captured requests from a webhook as a structured JSON array. "
            "Each entry includes headers, body, source IP, timestamp, method, URL, "
            "and user agent. Use this for archiving webhook data, feeding it into "
            "analysis pipelines, or creating test fixtures from real traffic."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to export.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of requests to include in the export. Default: 100.",
                    "default": 100,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="get_raw_request",
        title="Get Raw Request Body",
        description=(
            "Retrieve the raw, unprocessed body of a captured request with its original "
            "Content-Type intact (not JSON-wrapped). Returns the exact bytes the caller sent. "
            "Use this when you need the verbatim payload — for example, to inspect binary data, "
            "verify exact encoding, or replay a request to another endpoint. "
            "See also get_webhook_requests for the JSON-formatted version."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook that captured the request.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the specific captured request whose raw body to retrieve.",
                },
            },
            "required": ["webhook_token", "request_id"],
        },
    ),
    Tool(
        name="export_requests_csv",
        title="Export Requests as CSV",
        description=(
            "Export all captured requests from a webhook as a CSV file with up to 100,000 rows. "
            "The CSV includes columns for timestamp, method, URL, IP, headers, and body. "
            "Use this for bulk analysis in spreadsheets, importing into databases, or archiving "
            "webhook traffic. For JSON export, use export_webhook_data instead."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook whose requests to export as CSV.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="download_request_file",
        title="Download Request File Attachment",
        description=(
            "Download a file attachment from a captured request. Handles multipart form uploads, "
            "email attachments, and other file data embedded in incoming requests. "
            "Returns the file content with its original filename and MIME type. "
            "Use get_webhook_requests first to find the request_id and inspect its 'files' array "
            "for available file_ids."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook that captured the request.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the captured request containing the file.",
                },
                "file_id": {
                    "type": "string",
                    "description": "ID of the specific file attachment to download (from the request's 'files' array).",
                },
            },
            "required": ["webhook_token", "request_id", "file_id"],
        },
    ),
    Tool(
        name="update_request_note",
        title="Update Request Note",
        description=(
            "Add or update the note annotation on a captured request. Notes can hold up to "
            "10,000 characters and are useful for tagging requests with context, marking them "
            "for follow-up, or adding analysis comments. The note is visible in the webhook.site "
            "dashboard alongside the request."
        ),
        annotations=_UPDATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook containing the request.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the captured request to annotate.",
                },
                "note": {
                    "type": "string",
                    "description": "Note text to attach to the request (max 10,000 characters).",
                },
            },
            "required": ["webhook_token", "request_id", "note"],
        },
    ),
    Tool(
        name="extract_links_from_request",
        title="Extract Links from Request",
        description=(
            "Parse a captured request (typically an email) and extract all URLs found "
            "in its body. Returns a list of URLs with metadata. "
            "Use this to find password-reset links, email verification URLs, magic "
            "login links, or any other actionable URLs embedded in captured traffic. "
            "If no request_id is given, analyzes the most recent request."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook containing the request.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of a specific captured request to analyze. Defaults to the latest request.",
                },
                "filter_domain": {
                    "type": "string",
                    "description": "Only return URLs whose domain matches this value (e.g., 'example.com').",
                },
            },
            "required": ["webhook_token"],
        },
    ),

    # =========================================================================
    # DELETING REQUESTS
    # =========================================================================
    Tool(
        name="delete_request",
        title="Delete Single Request",
        description=(
            "Permanently delete one captured request from a webhook by its UUID. "
            "The request data (headers, body, metadata) is removed and cannot be recovered. "
            "Use this to clean up sensitive data or remove noise from your request log."
        ),
        annotations=_DELETE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook containing the request.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the specific request to delete.",
                },
            },
            "required": ["webhook_token", "request_id"],
        },
    ),
    Tool(
        name="delete_all_requests",
        title="Delete All Requests",
        description=(
            "Permanently delete all captured requests from a webhook. "
            "Optionally filter by date range or search query to delete only matching "
            "requests. Without filters, removes everything. This is irreversible. "
            "Use this to reset a webhook for a new test run or purge old data."
        ),
        annotations=_DELETE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to purge.",
                },
                "date_from": {
                    "type": "string",
                    "description": "Only delete requests after this datetime (yyyy-MM-dd HH:mm:ss or relative like 'now-7d').",
                },
                "date_to": {
                    "type": "string",
                    "description": "Only delete requests before this datetime (yyyy-MM-dd HH:mm:ss or relative like 'now-7d').",
                },
                "query": {
                    "type": "string",
                    "description": "Only delete requests matching this search query.",
                },
            },
            "required": ["webhook_token"],
        },
    ),

    # =========================================================================
    # REAL-TIME WAITING
    # =========================================================================
    Tool(
        name="wait_for_request",
        title="Wait for Incoming Request",
        description=(
            "Block until a new request arrives at the webhook, then return it. "
            "Uses server-sent events (SSE) for efficient real-time streaming instead "
            "of polling. Returns the full request details (method, headers, body, IP) "
            "as soon as it arrives, or times out after the specified duration. "
            "Use this after triggering a callback, webhook, or API integration to "
            "capture the resulting request."
        ),
        annotations=_WAIT,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to monitor.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Maximum seconds to wait before giving up. Default: 60.",
                    "default": 60,
                },
                "request_type": {
                    "type": "string",
                    "description": "Only return requests of this type. Omit to accept any type.",
                    "enum": ["web", "email", "dns"],
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="wait_for_email",
        title="Wait for Incoming Email",
        description=(
            "Block until an email arrives at {token}@email.webhook.site, then return it. "
            "Uses server-sent events (SSE) for real-time delivery. Returns the email "
            "subject, sender, body (text and HTML), and headers. "
            "Optionally extracts all URLs from the email body, which is especially useful "
            "for capturing magic login links, verification URLs, or password-reset links. "
            "Times out after the specified duration if no email arrives."
        ),
        annotations=_WAIT,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook whose email address to monitor.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Maximum seconds to wait before giving up. Default: 60.",
                    "default": 60,
                },
                "extract_links": {
                    "type": "boolean",
                    "description": "When true, parses all URLs from the email body and returns them separately. Default: true.",
                    "default": True,
                },
            },
            "required": ["webhook_token"],
        },
    ),

    # =========================================================================
    # SECURITY TESTING / BUG BOUNTY
    # =========================================================================
    Tool(
        name="generate_ssrf_payload",
        title="Generate SSRF Test Payloads",
        description=(
            "Generate a set of SSRF (Server-Side Request Forgery) test payloads tied "
            "to your webhook. Creates uniquely identifiable URLs in multiple formats "
            "(HTTP, DNS, IP-literal) that you can inject into target parameters to "
            "detect blind SSRF vulnerabilities. Each payload includes a custom identifier "
            "so you can trace which injection point triggered a callback. "
            "Check results with check_for_callbacks."
        ),
        annotations=_GENERATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook that will receive SSRF callbacks.",
                },
                "identifier": {
                    "type": "string",
                    "description": "Label to embed in payloads for tracing (e.g., 'profile-image-url', 'import-feed').",
                },
                "include_dns": {
                    "type": "boolean",
                    "description": "Include DNS-based payloads for detecting SSRF that blocks HTTP but allows DNS. Default: true.",
                    "default": True,
                },
                "include_ip": {
                    "type": "boolean",
                    "description": "Include IP-literal payloads to bypass domain-based allowlists. Default: true.",
                    "default": True,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="check_for_callbacks",
        title="Check for OOB Callbacks",
        description=(
            "Check whether any out-of-band (OOB) callbacks have been received on "
            "a webhook within a recent time window. Returns a count and summary of "
            "matching requests. Use this after injecting SSRF, XXE, or blind injection "
            "payloads to see if any triggered a callback. Optionally filter by a "
            "specific identifier to match a particular payload."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to check for callbacks.",
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "Only check requests from the last N minutes. Default: 60.",
                    "default": 60,
                },
                "identifier": {
                    "type": "string",
                    "description": "Filter for this identifier string in the request URL or body.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="generate_xss_callback",
        title="Generate XSS Callback Payloads",
        description=(
            "Generate JavaScript payloads that phone home to your webhook when executed "
            "in a victim's browser. Useful for detecting blind XSS vulnerabilities where "
            "the injected script runs in a context you cannot directly observe. "
            "Payloads can optionally exfiltrate cookies and DOM info (URL, referrer). "
            "Each payload includes a custom identifier to trace which injection point fired. "
            "Check results with check_for_callbacks."
        ),
        annotations=_GENERATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook that will receive XSS callbacks.",
                },
                "identifier": {
                    "type": "string",
                    "description": "Label to trace which injection point triggered (e.g., 'comment-field', 'profile-bio').",
                },
                "include_cookies": {
                    "type": "boolean",
                    "description": "Include a payload variant that sends document.cookie. Default: true.",
                    "default": True,
                },
                "include_dom": {
                    "type": "boolean",
                    "description": "Include a payload variant that sends document.URL and document.referrer. Default: true.",
                    "default": True,
                },
            },
            "required": ["webhook_token"],
        },
    ),
    # =========================================================================
    # CUSTOM ACTIONS
    # =========================================================================
    Tool(
        name="list_custom_actions",
        title="List Custom Actions",
        description=(
            "List all Custom Actions configured on a webhook token. "
            "Returns each action's UUID, type, execution order, parameters, and "
            "enabled/disabled state. Use this to audit the automation rules on a "
            "webhook before modifying or debugging them."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook whose Custom Actions to list.",
                },
            },
            "required": ["webhook_token"],
        },
    ),
    Tool(
        name="create_custom_action",
        title="Create Custom Action",
        description=(
            "Create a new Custom Action on a webhook token. Custom Actions are "
            "server-side automation rules that fire when the webhook receives a "
            "request. Supported types include 'condition' (conditional logic), "
            "'script' (WebhookScript), 'http_request' (HTTP forwarding), 'email', "
            "'slack', 'discord', 'google_sheets', and many more. The 'parameters' "
            "object varies by action type — see webhook.site docs for each type's "
            "schema. Actions execute in 'order' priority (lowest first)."
        ),
        annotations=_CREATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to add the action to.",
                },
                "type": {
                    "type": "string",
                    "description": (
                        "Action type name. Common types: 'condition', 'script', "
                        "'http_request', 'email', 'slack', 'discord', "
                        "'google_sheets', 'database_query', 'set_variable', "
                        "'extract_jsonpath', 'extract_regex', 'modify_response', "
                        "'rate_limit', 'log'."
                    ),
                },
                "order": {
                    "type": "integer",
                    "description": "Execution priority (lower runs first). Default: 0.",
                    "default": 0,
                },
                "parameters": {
                    "type": "object",
                    "description": (
                        "Type-specific configuration object. For 'condition': "
                        "{input, operator, value, action}. For 'script': {script}. "
                        "For 'http_request': {url, method, headers, body}. "
                        "See webhook.site Action Types docs for full schemas."
                    ),
                },
                "disabled": {
                    "type": "boolean",
                    "description": "When true, the action is skipped during execution. Default: false.",
                    "default": False,
                },
                "queue": {
                    "type": "boolean",
                    "description": "When true, the action runs asynchronously. Default: false.",
                    "default": False,
                },
                "delay": {
                    "type": "integer",
                    "description": "Seconds to wait before running (requires queue=true, max 86400).",
                },
                "condition": {
                    "type": "string",
                    "description": "UUID of a Condition action that gates this action. If the condition fails, this action is skipped.",
                },
            },
            "required": ["webhook_token", "type"],
        },
    ),
    Tool(
        name="update_custom_action",
        title="Update Custom Action",
        description=(
            "Update an existing Custom Action's configuration. You can change the "
            "action type, execution order, parameters, disabled state, queue mode, "
            "delay, and condition gate. Only the fields you provide are sent; omitted "
            "fields are left to the API's default merge behavior."
        ),
        annotations=_UPDATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook containing the action.",
                },
                "action_id": {
                    "type": "string",
                    "description": "UUID of the Custom Action to update.",
                },
                "type": {
                    "type": "string",
                    "description": "New action type name.",
                },
                "order": {
                    "type": "integer",
                    "description": "New execution priority (lower runs first).",
                },
                "parameters": {
                    "type": "object",
                    "description": "New type-specific configuration object.",
                },
                "disabled": {
                    "type": "boolean",
                    "description": "New disabled state.",
                },
                "queue": {
                    "type": "boolean",
                    "description": "New async execution flag.",
                },
                "delay": {
                    "type": "integer",
                    "description": "New delay in seconds (requires queue=true, max 86400).",
                },
                "condition": {
                    "type": "string",
                    "description": "UUID of a Condition action to gate this action.",
                },
            },
            "required": ["webhook_token", "action_id"],
        },
    ),
    Tool(
        name="delete_custom_action",
        title="Delete Custom Action",
        description=(
            "Permanently delete a Custom Action from a webhook token. The action is "
            "removed immediately and will no longer fire on incoming requests. "
            "This is irreversible — use list_custom_actions first to confirm the "
            "action UUID."
        ),
        annotations=_DELETE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook containing the action.",
                },
                "action_id": {
                    "type": "string",
                    "description": "UUID of the Custom Action to delete.",
                },
            },
            "required": ["webhook_token", "action_id"],
        },
    ),
    Tool(
        name="test_custom_action",
        title="Test Custom Action",
        description=(
            "Test a Custom Action with sample request data without saving it to the "
            "token. Executes the action definition you provide and returns the output, "
            "modified response, and resulting variables. Optionally base the test on an "
            "existing captured request and/or overwrite the parameters of an existing "
            "saved action. Use this to iterate on action logic before committing it."
        ),
        annotations=_SEND,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook to test against.",
                },
                "type": {
                    "type": "string",
                    "description": "Action type to test (e.g. 'script', 'condition', 'http_request').",
                },
                "order": {
                    "type": "integer",
                    "description": "Execution order for the test run. Default: 0.",
                    "default": 0,
                },
                "parameters": {
                    "type": "object",
                    "description": "Type-specific configuration to test (e.g. {script: \"echo('hello')\"} for WebhookScript).",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of a captured request to use as test input. If omitted, uses default request variables.",
                },
                "action_id": {
                    "type": "string",
                    "description": "UUID of an existing action whose parameters to overwrite for this test run.",
                },
            },
            "required": ["webhook_token", "type"],
        },
    ),
    Tool(
        name="execute_custom_actions",
        title="Execute Custom Actions on Request",
        description=(
            "Execute all Custom Actions configured on a webhook token against a "
            "specific captured request. Runs every enabled action in order and returns "
            "their combined output, any modified response, and resulting variables. "
            "Use this to replay automation on past traffic or re-trigger actions after "
            "updating their configuration."
        ),
        annotations=_SEND,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook whose actions to execute.",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the captured request to run actions against.",
                },
                "error_notifications": {
                    "type": "boolean",
                    "description": "When true, sends an email notification if an error occurs during execution. Default: false.",
                    "default": False,
                },
            },
            "required": ["webhook_token", "request_id"],
        },
    ),

    # =========================================================================
    # SECURITY TESTING / BUG BOUNTY
    # =========================================================================
    # =========================================================================
    # GLOBAL VARIABLES
    # =========================================================================
    Tool(
        name="list_global_variables",
        title="List Global Variables",
        description=(
            "List all global variables for the authenticated user. "
            "Global variables persist across all webhooks and schedules, making them "
            "ideal for shared configuration (API keys, base URLs, counters). "
            "Returns each variable's UUID, name, value, and created/updated timestamps. "
            "Requires an API key."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="create_global_variable",
        title="Create Global Variable",
        description=(
            "Create a new global variable that persists across all webhooks and schedules. "
            "Variables are accessible in Custom Actions and WebhookScript via $variable.name$ "
            "syntax. Use this for shared configuration like API keys, base URLs, environment "
            "flags, or counters that multiple webhooks need to reference."
        ),
        annotations=_CREATE,
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Variable name (used as $variable.name$ in scripts and actions).",
                },
                "value": {
                    "type": "string",
                    "description": "Variable value (string).",
                },
            },
            "required": ["name", "value"],
        },
    ),
    Tool(
        name="update_global_variable",
        title="Update Global Variable",
        description=(
            "Update the name or value of an existing global variable. "
            "Changes take effect immediately for all webhooks and schedules that "
            "reference this variable. Use list_global_variables to find the variable UUID."
        ),
        annotations=_UPDATE,
        inputSchema={
            "type": "object",
            "properties": {
                "variable_id": {
                    "type": "string",
                    "description": "UUID of the global variable to update.",
                },
                "name": {
                    "type": "string",
                    "description": "New variable name.",
                },
                "value": {
                    "type": "string",
                    "description": "New variable value.",
                },
            },
            "required": ["variable_id"],
        },
    ),
    Tool(
        name="delete_global_variable",
        title="Delete Global Variable",
        description=(
            "Permanently delete a global variable. Any webhooks or schedules referencing "
            "this variable via $variable.name$ will receive an empty value after deletion. "
            "This action is irreversible. Use list_global_variables to confirm the UUID."
        ),
        annotations=_DELETE,
        inputSchema={
            "type": "object",
            "properties": {
                "variable_id": {
                    "type": "string",
                    "description": "UUID of the global variable to delete.",
                },
            },
            "required": ["variable_id"],
        },
    ),

    # =========================================================================
    # SCHEDULES
    # =========================================================================
    Tool(
        name="list_schedules",
        title="List Schedules",
        description=(
            "List all scheduled tasks for the authenticated user. "
            "Schedules are cron-based HTTP requests that run on a timer — useful for "
            "health checks, periodic API polling, data sync jobs, or keep-alive pings. "
            "Returns each schedule's UUID, name, interval, target URL, method, and "
            "enabled state. Requires an API key."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="create_schedule",
        title="Create Schedule",
        description=(
            "Create a new scheduled task that sends HTTP requests on a timer. "
            "Supports preset intervals (monthly, weekly, daily, hourly, 10-minute, "
            "5-minute, 1-minute) or custom cron expressions. Each execution sends an "
            "HTTP request to the specified URL with optional headers and body. "
            "Use this for uptime monitoring, periodic API calls, or automated data pushes."
        ),
        annotations=_CREATE,
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Human-readable name for the schedule.",
                },
                "interval": {
                    "type": "string",
                    "description": (
                        "Execution frequency. Presets: 'monthly', 'weekly', 'daily', "
                        "'hourly', '10-minute', '5-minute', '1-minute'. "
                        "Or use 'cron' and provide a cron expression in the 'cron' parameter."
                    ),
                },
                "cron": {
                    "type": "string",
                    "description": "Custom cron expression (e.g. '0 */2 * * *' for every 2 hours). Only used when interval is 'cron'.",
                },
                "request_url": {
                    "type": "string",
                    "description": "Target URL to send the scheduled request to.",
                },
                "request_method": {
                    "type": "string",
                    "description": "HTTP method for the scheduled request. Default: GET.",
                    "default": "GET",
                },
                "request_body": {
                    "type": "string",
                    "description": "Request body for POST/PUT/PATCH requests.",
                },
                "request_headers": {
                    "type": "string",
                    "description": "Request headers as newline-separated 'Key: Value' pairs.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (1-30). Default: 10.",
                    "default": 10,
                },
            },
            "required": ["name", "request_url"],
        },
    ),
    Tool(
        name="run_schedule_now",
        title="Run Schedule Now",
        description=(
            "Trigger immediate execution of a scheduled task, bypassing its normal timer. "
            "The request is sent to the schedule's configured URL with its headers and body. "
            "Use this to test a schedule configuration or force a run outside its normal cycle."
        ),
        annotations=_SEND,
        inputSchema={
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "UUID of the schedule to run immediately.",
                },
            },
            "required": ["schedule_id"],
        },
    ),
    Tool(
        name="get_schedule_logs",
        title="Get Schedule Logs",
        description=(
            "Retrieve execution logs for a scheduled task. Each log entry includes "
            "the execution timestamp, HTTP status code, response body, and whether the "
            "run succeeded or failed. Use this to debug schedule failures or verify "
            "that scheduled requests are landing correctly."
        ),
        annotations=_READONLY,
        inputSchema={
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "UUID of the schedule whose logs to retrieve.",
                },
                "sorting": {
                    "type": "string",
                    "description": "Sort order: 'newest' (default) or 'oldest'.",
                    "default": "newest",
                },
            },
            "required": ["schedule_id"],
        },
    ),

    # =========================================================================
    # DYNAMIC RESPONSE
    # =========================================================================
    Tool(
        name="set_dynamic_response",
        title="Set Dynamic Response",
        description=(
            "Dynamically set the HTTP response for a specific incoming request. "
            "Only works when the webhook token has 'listen' > 0, which causes the "
            "webhook to hold the caller's connection open until you provide a response "
            "via this endpoint. The content is automatically base64-encoded before sending. "
            "Use this for programmatic request/response flows — e.g., a mock API that "
            "inspects the request and returns a tailored response, or an approval workflow "
            "that holds a webhook call until a human decides."
        ),
        annotations=_UPDATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook (must have listen > 0).",
                },
                "request_id": {
                    "type": "string",
                    "description": "UUID of the incoming request to respond to.",
                },
                "status": {
                    "type": "integer",
                    "description": "HTTP status code to return to the caller (200-599). Default: 200.",
                    "default": 200,
                },
                "content": {
                    "type": "string",
                    "description": "Response body to return to the caller (plain text — will be base64-encoded automatically).",
                    "default": "",
                },
                "content_type": {
                    "type": "string",
                    "description": "Content-Type header for the response. Default: text/plain.",
                    "default": "text/plain",
                },
                "headers": {
                    "type": "object",
                    "description": "Additional response headers as key-value pairs.",
                    "default": {},
                },
            },
            "required": ["webhook_token", "request_id"],
        },
    ),

    # =========================================================================
    # SECURITY TESTING / BUG BOUNTY
    # =========================================================================
    Tool(
        name="generate_canary_token",
        title="Generate Canary Token",
        description=(
            "Create a trackable canary token (URL, DNS domain, or email address) tied "
            "to your webhook. When someone accesses the canary, it triggers a callback "
            "you can detect with check_for_callbacks. "
            "Use this for detecting unauthorized document access, data leakage, or "
            "honeypot monitoring. Each token can carry a custom identifier for context."
        ),
        annotations=_GENERATE,
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_token": {
                    "type": "string",
                    "description": "UUID token of the webhook that will receive canary alerts.",
                },
                "token_type": {
                    "type": "string",
                    "description": "Canary type: 'url' (web link), 'dns' (DNS lookup trigger), or 'email' (email open tracker).",
                    "enum": ["url", "dns", "email"],
                    "default": "url",
                },
                "identifier": {
                    "type": "string",
                    "description": "Label for this canary (e.g., 'confidential-doc-v3', 'admin-creds-file').",
                },
            },
            "required": ["webhook_token"],
        },
    ),
]
