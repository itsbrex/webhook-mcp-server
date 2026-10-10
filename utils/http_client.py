"""
HTTP client utilities for webhook.site API interactions.

Provides a centralized, async HTTP client with proper error handling,
timeout configuration, and consistent header management.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

# API Configuration
WEBHOOK_SITE_API = "https://webhook.site"
DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Rate-limit / transient-failure retry policy.
# webhook.site enforces per-endpoint rate limits (e.g. 120/min on requests,
# 10/min on token creation and bulk delete, 3/min on CSV export) and returns
# HTTP 429 with a Retry-After header when exceeded. Transient 5xx responses and
# connection errors are also retried with exponential backoff.
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5  # seconds; doubled each attempt
MAX_RETRY_AFTER = 30.0    # cap honored Retry-After wait so a tool never hangs
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class WebhookApiError(Exception):
    """Custom exception for webhook.site API errors.
    
    Args:
        message: Error description
        status_code: HTTP status code (if applicable)
        response_body: Raw response body (if available)
    """
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WebhookHttpClient:
    """Async HTTP client for webhook.site API.
    
    Provides methods for common HTTP operations with consistent
    error handling and configuration.
    
    Usage:
        async with WebhookHttpClient() as client:
            response = await client.get("/token/abc123")
    """
    
    def __init__(
        self,
        base_url: str = WEBHOOK_SITE_API,
        timeout: float = DEFAULT_TIMEOUT,
        api_key: str | None = None,
    ) -> None:
        """Initialize the HTTP client.
        
        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            api_key: Optional API key for authenticated requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> WebhookHttpClient:
        """Enter async context manager."""
        headers = DEFAULT_HEADERS.copy()
        if self.api_key:
            headers["Api-Key"] = self.api_key
        
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
            # webhook.site returns 302/304 redirects for file downloads; without
            # this, download_request_file would receive an empty redirect body.
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the underlying httpx client."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client
    
    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"

    @staticmethod
    def _parse_retry_after(response: httpx.Response, attempt: int) -> float:
        """Determine how long to wait before retrying.

        Honors the server's Retry-After header (seconds form) on 429, capped at
        MAX_RETRY_AFTER. Falls back to exponential backoff otherwise.
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), MAX_RETRY_AFTER)
            except ValueError:
                pass  # HTTP-date form is uncommon here; fall through to backoff
        return RETRY_BACKOFF_BASE * (2 ** attempt)

    async def _send(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a request, retrying on rate limits and transient failures.

        Retries HTTP 429 (honoring Retry-After) and transient 5xx responses, as
        well as connection errors, up to MAX_RETRIES times with exponential
        backoff. Does not call raise_for_status(); callers decide how to handle
        the final response.
        """
        last_error: httpx.RequestError | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.RequestError as e:
                last_error = e
                if attempt >= MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_BACKOFF_BASE * (2 ** attempt))
                continue

            if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                await asyncio.sleep(self._parse_retry_after(response, attempt))
                continue
            return response

        # Unreachable: loop either returns or raises, but satisfies type checker.
        raise WebhookApiError(f"Request failed after retries: {last_error}")
    
    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform GET request.
        
        Args:
            path: API path (e.g., "/token/abc123")
            params: Query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "GET",
                self._build_url(path),
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise WebhookApiError(
                f"GET {path} failed: {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            raise WebhookApiError(f"Request failed: {str(e)}") from e
    
    async def post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform POST request.
        
        Args:
            path: API path
            json_data: JSON body data
            headers: Additional headers
            
        Returns:
            Full httpx Response object
            
        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "POST",
                self._build_url(path),
                json=json_data,
                headers=headers,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            raise WebhookApiError(
                f"POST {path} failed: {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            raise WebhookApiError(f"POST request failed: {str(e)}") from e
    
    async def put(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform PUT request.
        
        Args:
            path: API path
            json_data: JSON body data
            
        Returns:
            Parsed JSON response
            
        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "PUT",
                self._build_url(path),
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise WebhookApiError(
                f"PUT {path} failed: {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            raise WebhookApiError(f"PUT request failed: {str(e)}") from e
    
    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> int:
        """Perform DELETE request.
        
        Args:
            path: API path
            params: Query parameters
            
        Returns:
            HTTP status code
            
        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "DELETE",
                self._build_url(path),
                params=params,
            )
            return response.status_code
        except httpx.RequestError as e:
            raise WebhookApiError(f"DELETE request failed: {str(e)}") from e
    
    async def get_raw(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Perform GET request and return the full Response without JSON parsing.

        Use this for endpoints that return non-JSON content (raw text, CSV, binary files).

        Args:
            path: API path (e.g., "/token/{id}/request/{rid}/raw")
            params: Query parameters

        Returns:
            Full httpx Response object (access .text, .content, .headers as needed)

        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "GET",
                self._build_url(path),
                params=params,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            raise WebhookApiError(
                f"GET {path} failed: {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
        except httpx.RequestError as e:
            raise WebhookApiError(f"GET raw request failed: {str(e)}") from e

    async def post_raw(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform POST request to an absolute URL (not using base_url).
        
        Useful for posting to webhook endpoints directly.
        
        Args:
            url: Full URL to POST to
            json: JSON body data
            headers: Additional headers
            
        Returns:
            Full httpx Response object
            
        Raises:
            WebhookApiError: On HTTP or API errors
        """
        try:
            response = await self._send(
                "POST",
                url,
                json=json,
                headers=headers,
            )
            return response
        except httpx.RequestError as e:
            raise WebhookApiError(f"POST request failed: {str(e)}") from e
