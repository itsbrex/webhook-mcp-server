"""Offline tests for HTTP client rate-limit retry and redirect handling.

Uses httpx.MockTransport so no network or live webhook.site account is needed.
"""
from __future__ import annotations

import httpx
import pytest

from utils.http_client import (
    WebhookHttpClient,
    WebhookApiError,
    MAX_RETRY_AFTER,
)


def _client_with(transport: httpx.MockTransport) -> WebhookHttpClient:
    c = WebhookHttpClient()
    c._client = httpx.AsyncClient(transport=transport, follow_redirects=True)
    return c


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={})
        return httpx.Response(200, json={"data": [{"uuid": "x"}]})

    client = _client_with(httpx.MockTransport(handler))
    result = await client.get("/token/abc/requests")
    assert calls["n"] == 2  # retried exactly once
    assert result["data"][0]["uuid"] == "x"
    await client._client.aclose()


@pytest.mark.asyncio
async def test_gives_up_after_max_retries_on_persistent_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0"}, json={})

    client = _client_with(httpx.MockTransport(handler))
    with pytest.raises(WebhookApiError) as exc:
        await client.get("/token/abc/requests")
    assert exc.value.status_code == 429
    await client._client.aclose()


@pytest.mark.asyncio
async def test_retry_after_is_capped():
    resp = httpx.Response(429, headers={"Retry-After": "99999"})
    wait = WebhookHttpClient._parse_retry_after(resp, attempt=0)
    assert wait == MAX_RETRY_AFTER


@pytest.mark.asyncio
async def test_follow_redirects_enabled_for_downloads():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/download/f1"):
            return httpx.Response(302, headers={"Location": "/cdn/file"})
        return httpx.Response(200, content=b"FILECONTENTS",
                              headers={"content-type": "text/plain"})

    client = _client_with(httpx.MockTransport(handler))
    resp = await client.get_raw("/token/abc/request/r1/download/f1")
    assert resp.status_code == 200
    assert resp.text == "FILECONTENTS"
    await client._client.aclose()
