"""
Request service for managing webhook requests.

Handles retrieval, search, and deletion of requests
captured by webhook.site endpoints.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from models.schemas import SearchFilters, DeleteFilters, ToolResult
from utils.http_client import WebhookHttpClient

# Constants for request handling
DEFAULT_REQUEST_LIMIT = 10
DEFAULT_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2.0


class RequestService:
    """Service for webhook request operations.
    
    Provides business logic for:
    - Listing all requests
    - Searching requests with filters
    - Getting latest request
    - Deleting individual requests
    - Bulk deleting requests
    """
    
    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.
        
        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client
    
    async def get_all(
        self,
        webhook_token: str,
        limit: int = DEFAULT_REQUEST_LIMIT,
        request_type: str | None = None,
    ) -> ToolResult:
        """Get all requests sent to a webhook.
        
        Args:
            webhook_token: The webhook UUID
            limit: Maximum number of requests to retrieve
            request_type: Filter by type ('web', 'email', 'dns')
            
        Returns:
            ToolResult with list of requests
        """
        params: dict[str, Any] = {"per_page": limit}
        if request_type:
            params["query"] = f"type:{request_type}"
        
        data = await self._client.get(
            f"/token/{webhook_token}/requests",
            params=params,
        )
        
        requests_data = data.get("data", [])
        requests = [
            self._format_request(req)
            for req in requests_data
        ]
        
        return ToolResult(
            success=True,
            message=f"Retrieved {len(requests)} requests",
            data={
                "total_requests": len(requests),
                "requests": requests,
            }
        )
    
    async def search(
        self,
        webhook_token: str,
        filters: SearchFilters,
    ) -> ToolResult:
        """Search requests with query filters.
        
        Args:
            webhook_token: The webhook UUID
            filters: SearchFilters with query, date range, etc.
            
        Returns:
            ToolResult with matching requests
        """
        data = await self._client.get(
            f"/token/{webhook_token}/requests",
            params=filters.to_params(),
        )
        
        requests_data = data.get("data", [])
        requests = [
            self._format_request(req)
            for req in requests_data
        ]
        
        return ToolResult(
            success=True,
            message=f"Found {len(requests)} matching requests",
            data={
                "query": filters.query,
                "total_found": len(requests),
                "requests": requests,
            }
        )
    
    async def get_latest(self, webhook_token: str) -> ToolResult:
        """Get the most recent request to a webhook.
        
        Args:
            webhook_token: The webhook UUID
            
        Returns:
            ToolResult with latest request or None
        """
        data = await self._client.get(
            f"/token/{webhook_token}/requests",
            params={"per_page": 1},
        )
        
        requests_data = data.get("data", [])
        
        if not requests_data:
            return ToolResult(
                success=True,
                message="No requests found for this webhook",
                data={"request": None}
            )
        
        request = self._format_request(requests_data[0])
        
        return ToolResult(
            success=True,
            message="Latest request retrieved",
            data={"request": request}
        )
    
    async def delete_one(
        self,
        webhook_token: str,
        request_id: str,
    ) -> ToolResult:
        """Delete a specific request.
        
        Args:
            webhook_token: The webhook UUID
            request_id: The request UUID to delete
            
        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/token/{webhook_token}/request/{request_id}"
        )
        success = status_code in [200, 204]
        
        return ToolResult(
            success=success,
            message="Request deleted successfully" if success else "Failed to delete request",
            data={
                "request_id": request_id,
                "status_code": status_code,
            }
        )
    
    async def delete_all(
        self,
        webhook_token: str,
        filters: DeleteFilters | None = None,
    ) -> ToolResult:
        """Delete all requests, optionally filtered.
        
        Args:
            webhook_token: The webhook UUID
            filters: Optional DeleteFilters for date range/query
            
        Returns:
            ToolResult indicating success/failure
        """
        params = filters.to_params() if filters else {}
        
        status_code = await self._client.delete(
            f"/token/{webhook_token}/request",
            params=params if params else None,
        )
        success = status_code in [200, 204]
        
        filter_desc = ""
        if params:
            filter_desc = f" matching filters: {params}"
        
        return ToolResult(
            success=success,
            message=f"Requests deleted successfully{filter_desc}" if success else "Failed to delete requests",
            data={
                "filters_applied": params if params else "none (all requests)",
                "status_code": status_code,
            }
        )
    
    @staticmethod
    def _format_request(req: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API request into clean output.
        
        Handles missing or None values gracefully to prevent crashes.
        
        Args:
            req: Raw request data from API
            
        Returns:
            Formatted request dictionary with safe defaults
        """
        return {
            "uuid": req.get("uuid", "unknown"),
            "type": req.get("type", "unknown"),
            "method": req.get("method", "UNKNOWN"),
            "content": req.get("content") if req.get("content") is not None else "",
            "text_content": req.get("text_content"),
            "html_content": req.get("html_content"),
            "headers": req.get("headers", {}),
            "query": req.get("query", {}),
            "url": req.get("url", ""),
            "ip": req.get("ip", "unknown"),
            "created_at": req.get("created_at", "unknown"),
        }
    
    async def wait_for_request(
        self,
        webhook_token: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        request_type: str | None = None,
    ) -> ToolResult:
        """Wait for a new HTTP request to be received by the webhook.
        
        SMART BEHAVIOR: First checks for existing requests and returns immediately
        if any are found. Only waits/polls if no matching requests exist yet.
        
        Args:
            webhook_token: The webhook UUID
            timeout_seconds: Maximum time to wait (default: 60)
            request_type: Filter by type ('web', 'email', 'dns'). None for any.
            
        Returns:
            ToolResult with the received request or timeout message
        """
        import time
        from utils.http_client import WebhookApiError
        
        poll_interval = POLL_INTERVAL_SECONDS
        max_retries = 3
        retry_count = 0
        
        # SMART CHECK: First look for existing requests before waiting
        try:
            initial_data = await self._client.get(
                f"/token/{webhook_token}/requests",
                params={"per_page": 5, "sorting": "newest"},
            )
            initial_requests = initial_data.get("data", [])
            
            # Check if there's already a matching request - return immediately!
            for req in initial_requests:
                # Check type filter
                if request_type and req.get("type") != request_type:
                    continue
                    
                # Found a matching request - return it immediately
                formatted = self._format_request(req)
                return ToolResult(
                    success=True,
                    message=f"Request found (already received, type: {req.get('type', 'unknown')})",
                    data={"request": formatted, "waited": False}
                )
            
            # No matching requests yet - track newest ID for polling
            initial_newest_id = initial_requests[0].get("uuid") if initial_requests else None
            
        except WebhookApiError as e:
            return ToolResult(
                success=False,
                message=f"Failed to initialize polling: {e}",
                data={"error": str(e)}
            )
        
        # No existing match found - start polling
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            await asyncio.sleep(poll_interval)
            
            try:
                # Check for new requests
                data = await self._client.get(
                    f"/token/{webhook_token}/requests",
                    params={"per_page": 5, "sorting": "newest"},
                )
                retry_count = 0  # Reset retry count on success
                
                requests = data.get("data", [])
                
                # Find new requests (after initial_newest_id)
                for req in requests:
                    if req.get("uuid") == initial_newest_id:
                        break  # Reached old requests
                    
                    # Check type filter
                    if request_type and req.get("type") != request_type:
                        continue
                    
                    formatted = self._format_request(req)
                    return ToolResult(
                        success=True,
                        message=f"Request received (type: {req.get('type', 'unknown')})",
                        data={"request": formatted}
                    )
                    
            except WebhookApiError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return ToolResult(
                        success=False,
                        message=f"API error during polling (after {max_retries} retries): {e}",
                        data={"error": str(e)}
                    )
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
                continue
        
        type_desc = f" of type '{request_type}'" if request_type else ""
        return ToolResult(
            success=False,
            message=f"Timeout: No request{type_desc} received within {timeout_seconds} seconds",
            data={"timeout": True, "request": None}
        )
    
    async def wait_for_email(
        self,
        webhook_token: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        extract_links: bool = True,
    ) -> ToolResult:
        """Wait for an email to be received at the webhook's email address.
        
        The email address format is: {token}@email.webhook.site
        
        SMART BEHAVIOR: First checks for existing emails and returns immediately
        if any are found. Only waits/polls if no emails exist yet.
        
        Args:
            webhook_token: The webhook UUID
            timeout_seconds: Maximum time to wait (default: 60)
            extract_links: If True, extract all URLs from the email body
            
        Returns:
            ToolResult with the email content and extracted links
        """
        import time
        from utils.http_client import WebhookApiError
        
        poll_interval = POLL_INTERVAL_SECONDS
        max_retries = 3
        retry_count = 0
        
        # SMART CHECK: First look for existing emails before waiting
        try:
            initial_data = await self._client.get(
                f"/token/{webhook_token}/requests",
                params={"per_page": 10, "sorting": "newest"},
            )
            initial_requests = initial_data.get("data", [])
            
            # Check if there's already an email - return immediately!
            for req in initial_requests:
                if req.get("type") == "email":
                    # Found an existing email - return it immediately
                    email_data = {
                        "uuid": req.get("uuid"),
                        "from": self._extract_header(req, "from"),
                        "subject": self._extract_header(req, "subject"),
                        "text_content": req.get("text_content"),
                        "html_content": req.get("html_content"),
                        "created_at": req.get("created_at"),
                    }
                    
                    # Extract links if requested
                    links = []
                    if extract_links:
                        content = req.get("text_content") or req.get("html_content") or ""
                        url_pattern = r'https?://[^\s<>"\']+(?:[?&][^\s<>"\']+)*'
                        links = list(set(re.findall(url_pattern, content)))
                        auth_links = [l for l in links if any(kw in l.lower() for kw in ['magic', 'auth', 'token', 'verify', 'confirm'])]
                        email_data["auth_links"] = auth_links
                    
                    email_data["all_links"] = links
                    
                    return ToolResult(
                        success=True,
                        message=f"Email found (already received): {email_data['subject']}",
                        data={"email": email_data, "waited": False}
                    )
            
            # No emails yet - track IDs for polling
            initial_email_ids: set[str] = set()  # No emails exist yet
            
        except WebhookApiError as e:
            return ToolResult(
                success=False,
                message=f"Failed to initialize email polling: {e}",
                data={"error": str(e)}
            )
        
        # No existing email found - start polling
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            await asyncio.sleep(poll_interval)
            
            try:
                # Check for new emails
                data = await self._client.get(
                    f"/token/{webhook_token}/requests",
                    params={"per_page": 10, "sorting": "newest"},
                )
                retry_count = 0  # Reset on success
                
                requests = data.get("data", [])
                
                # Find new emails
                for req in requests:
                    if req.get("type") != "email":
                        continue
                    if req.get("uuid") in initial_email_ids:
                        continue  # Already seen this email
                    
                    # Found a new email!
                    email_data = {
                        "uuid": req.get("uuid"),
                        "from": self._extract_header(req, "from"),
                        "subject": self._extract_header(req, "subject"),
                        "text_content": req.get("text_content"),
                        "html_content": req.get("html_content"),
                        "created_at": req.get("created_at"),
                    }
                    
                    # Extract links if requested
                    links = []
                    if extract_links:
                        content = req.get("text_content") or req.get("html_content") or ""
                        url_pattern = r'https?://[^\s<>"\']+(?:[?&][^\s<>"\']+)*'
                        links = list(set(re.findall(url_pattern, content)))
                        
                        # Identify auth/magic links
                        auth_links = [l for l in links if any(kw in l.lower() for kw in ['magic', 'auth', 'token', 'verify', 'confirm'])]
                        email_data["auth_links"] = auth_links
                    
                    email_data["all_links"] = links
                    
                    return ToolResult(
                        success=True,
                        message=f"Email received: {email_data['subject']}",
                        data={"email": email_data}
                    )
                    
            except WebhookApiError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return ToolResult(
                        success=False,
                        message=f"API error during email polling (after {max_retries} retries): {e}",
                        data={"error": str(e)}
                    )
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
                continue
        
        return ToolResult(
            success=False,
            message=f"Timeout: No email received within {timeout_seconds} seconds",
            data={
                "timeout": True,
                "email": None,
                "email_address": f"{webhook_token}@email.webhook.site"
            }
        )
    
    async def get_raw_request(
        self,
        webhook_token: str,
        request_id: str,
    ) -> ToolResult:
        """Get the raw, unprocessed body of a captured request.

        Returns the original content with its native Content-Type,
        not wrapped in JSON.

        Args:
            webhook_token: The webhook UUID
            request_id: The request UUID

        Returns:
            ToolResult with raw body text and content type
        """
        response = await self._client.get_raw(
            f"/token/{webhook_token}/request/{request_id}/raw"
        )

        content_type = response.headers.get("content-type", "application/octet-stream")

        return ToolResult(
            success=True,
            message=f"Raw request body retrieved ({len(response.text)} chars, {content_type})",
            data={
                "request_id": request_id,
                "content_type": content_type,
                "body": response.text,
                "size_bytes": len(response.content),
            },
        )

    async def export_requests_csv(
        self,
        webhook_token: str,
    ) -> ToolResult:
        """Export all captured requests as CSV (up to 100,000 rows).

        Uses the native webhook.site CSV export endpoint.

        Args:
            webhook_token: The webhook UUID

        Returns:
            ToolResult with CSV content as text
        """
        response = await self._client.get_raw(
            f"/token/{webhook_token}/requests/export"
        )

        csv_text = response.text
        row_count = max(csv_text.count("\n") - 1, 0)  # subtract header row

        return ToolResult(
            success=True,
            message=f"Exported {row_count} requests as CSV",
            data={
                "webhook_token": webhook_token,
                "row_count": row_count,
                "csv": csv_text,
            },
        )

    async def download_request_file(
        self,
        webhook_token: str,
        request_id: str,
        file_id: str,
    ) -> ToolResult:
        """Download a file attachment from a captured request.

        Args:
            webhook_token: The webhook UUID
            request_id: The request UUID containing the file
            file_id: The file attachment ID

        Returns:
            ToolResult with file content, filename, and MIME type
        """
        response = await self._client.get_raw(
            f"/token/{webhook_token}/request/{request_id}/download/{file_id}"
        )

        content_type = response.headers.get("content-type", "application/octet-stream")

        # Try to extract filename from Content-Disposition header
        content_disp = response.headers.get("content-disposition", "")
        filename = "unknown"
        if "filename=" in content_disp:
            parts = content_disp.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip().strip('"')

        # For text-safe content, return as text; otherwise note it's binary
        is_text = content_type.startswith("text/") or content_type in (
            "application/json",
            "application/xml",
            "application/csv",
        )

        return ToolResult(
            success=True,
            message=f"Downloaded file '{filename}' ({content_type}, {len(response.content)} bytes)",
            data={
                "file_id": file_id,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(response.content),
                "content": response.text if is_text else f"[binary data, {len(response.content)} bytes]",
            },
        )

    async def update_request_note(
        self,
        webhook_token: str,
        request_id: str,
        note: str,
    ) -> ToolResult:
        """Update the note field on a captured request.

        Args:
            webhook_token: The webhook UUID
            request_id: The request UUID to annotate
            note: Note text (max 10,000 characters)

        Returns:
            ToolResult confirming the update
        """
        if len(note) > 10_000:
            return ToolResult(
                success=False,
                message=f"Note too long: {len(note)} chars (max 10,000)",
                data={"length": len(note)},
            )

        # NOTE: webhook.site's "Update Request" endpoint is the plural
        # /requests/{id} path (unlike GET/DELETE single-request, which are
        # singular /request/{id}). Using the singular path here 404s.
        data = await self._client.put(
            f"/token/{webhook_token}/requests/{request_id}",
            json_data={"note": note},
        )

        return ToolResult(
            success=True,
            message="Request note updated successfully",
            data={
                "request_id": request_id,
                "note": note,
                "note_length": len(note),
            },
        )

    async def send_multiple(
        self,
        webhook_token: str,
        payloads: list[dict[str, Any]],
        delay_ms: int = 0,
    ) -> ToolResult:
        """Send multiple requests to a webhook in batch.
        
        Useful for load testing or sending test payloads.
        
        Args:
            webhook_token: The webhook UUID
            payloads: List of JSON payloads to send
            delay_ms: Delay between requests in milliseconds (default: 0)
            
        Returns:
            ToolResult with success/failure counts
        """
        from utils.http_client import WEBHOOK_SITE_API
        
        results = []
        success_count = 0
        fail_count = 0
        
        for i, payload in enumerate(payloads):
            try:
                response = await self._client.post_raw(
                    f"{WEBHOOK_SITE_API}/{webhook_token}",
                    json=payload
                )
                results.append({
                    "index": i,
                    "success": True,
                    "status_code": response.status_code
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e)
                })
                fail_count += 1
            
            # Add delay between requests if specified
            if delay_ms > 0 and i < len(payloads) - 1:
                await asyncio.sleep(delay_ms / 1000.0)
        
        return ToolResult(
            success=fail_count == 0,
            message=f"Sent {success_count}/{len(payloads)} requests successfully",
            data={
                "total": len(payloads),
                "success_count": success_count,
                "fail_count": fail_count,
                "results": results
            }
        )
    
    async def export_requests(
        self,
        webhook_token: str,
        limit: int = 100,
        format: str = "json",
    ) -> ToolResult:
        """Export all requests from a webhook to JSON.
        
        Args:
            webhook_token: The webhook UUID
            limit: Maximum number of requests to export (default: 100)
            format: Export format (currently only 'json' supported)
            
        Returns:
            ToolResult with exported data
        """
        data = await self._client.get(
            f"/token/{webhook_token}/requests",
            params={"per_page": limit},
        )
        
        requests_data = data.get("data", [])
        
        # Format each request with full details
        export_data = []
        for req in requests_data:
            export_data.append({
                "uuid": req.get("uuid"),
                "type": req.get("type"),
                "method": req.get("method"),
                "url": req.get("url"),
                "ip": req.get("ip"),
                "hostname": req.get("hostname"),
                "headers": req.get("headers", {}),
                "query": req.get("query", {}),
                "content": req.get("content"),
                "text_content": req.get("text_content"),
                "created_at": req.get("created_at"),
                "user_agent": self._extract_header(req, "User-Agent"),
                "content_type": self._extract_header(req, "Content-Type"),
            })
        
        return ToolResult(
            success=True,
            message=f"Exported {len(export_data)} requests",
            data={
                "webhook_token": webhook_token,
                "export_format": format,
                "request_count": len(export_data),
                "requests": export_data
            }
        )
    
    async def set_dynamic_response(
        self,
        webhook_token: str,
        request_id: str,
        status: int = 200,
        content: str = "",
        content_type: str = "text/plain",
        headers: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Set the dynamic response for a specific incoming request.

        Only works when the webhook token has listen > 0. The webhook
        holds the caller's connection open until this response is provided.
        Content is base64-encoded before sending, as required by the API.

        Args:
            webhook_token: The webhook UUID (must have listen > 0)
            request_id: The request UUID to respond to
            status: HTTP status code (200-599)
            content: Response body (plain text, will be base64-encoded)
            content_type: Content-Type header value
            headers: Additional response headers

        Returns:
            ToolResult confirming the response was set
        """
        import base64

        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")

        response_headers = headers or {}
        response_headers["Content-Type"] = content_type

        payload = {
            "status": status,
            "content": encoded_content,
            "headers": response_headers,
        }

        data = await self._client.put(
            f"/token/{webhook_token}/requests/{request_id}/response",
            json_data=payload,
        )

        return ToolResult(
            success=True,
            message=f"Dynamic response set (status: {status}, {len(content)} chars)",
            data={
                "webhook_token": webhook_token,
                "request_id": request_id,
                "status": status,
                "content_type": content_type,
                "content_length": len(content),
            },
        )

    @staticmethod
    def _extract_header(req: dict[str, Any], header_name: str) -> str:
        """Extract a header value from a request."""
        headers = req.get("headers", {})
        if not headers:
            return "Unknown"
        value = headers.get(header_name, headers.get(header_name.title(), ["Unknown"]))
        if isinstance(value, list):
            return value[0] if value else "Unknown"
        return value or "Unknown"
