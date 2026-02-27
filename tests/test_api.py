from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

from app.services.og_service import OGData
from tests.conftest import FakeRedis

pytestmark = pytest.mark.asyncio


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["redis"] == "up"


async def test_shorten_returns_short_url(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "short_url" in body
    assert "short_code" in body
    assert body["original_url"] == "https://example.com/"


async def test_shorten_is_idempotent(client: AsyncClient) -> None:
    r1 = await client.post("/shorten", json={"url": "https://example.com"})
    r2 = await client.post("/shorten", json={"url": "https://example.com"})
    assert r1.json()["short_code"] == r2.json()["short_code"]


async def test_redirect(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["short_code"]

    redirect_resp = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_resp.status_code == 301
    assert redirect_resp.headers["location"] == "https://example.com/"


async def test_preview(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["short_code"]

    with patch("app.api.routes.fetch_og_data", new_callable=AsyncMock, return_value=OGData()):
        preview_resp = await client.get(f"/!{code}")
    assert preview_resp.status_code == 200
    assert "https://example.com/" in preview_resp.text
    assert "<a href=" in preview_resp.text


async def test_redirect_not_found(client: AsyncClient) -> None:
    resp = await client.get("/nonexistent", follow_redirects=False)
    assert resp.status_code == 404


async def test_preview_not_found(client: AsyncClient) -> None:
    resp = await client.get("/!nonexistent")
    assert resp.status_code == 404


async def test_shorten_invalid_url(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 422


async def test_response_contains_request_id_header(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert "x-request-id" in resp.headers


async def test_custom_request_id_is_preserved(client: AsyncClient) -> None:
    resp = await client.get("/health", headers={"X-Request-ID": "my-id-123"})
    assert resp.headers["x-request-id"] == "my-id-123"


async def test_rate_limit_headers_present(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers
    assert "x-ratelimit-reset" in resp.headers


async def test_rate_limit_exceeded_returns_429(client: AsyncClient) -> None:
    max_req = 5
    with patch("app.api.middleware.settings") as mock_settings:
        mock_settings.rate_limit_enabled = True
        mock_settings.rate_limit_max_requests = max_req
        mock_settings.rate_limit_window_seconds = 60

        for i in range(max_req):
            resp = await client.post("/shorten", json={"url": "https://example.com"})
            assert resp.status_code == 200, f"Request {i + 1} failed unexpectedly"

        resp = await client.post("/shorten", json={"url": "https://example.com"})
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded"
        assert "retry-after" in resp.headers


async def test_health_endpoint_bypasses_rate_limit(client: AsyncClient) -> None:
    max_req = 2
    with patch("app.api.middleware.settings") as mock_settings:
        mock_settings.rate_limit_enabled = True
        mock_settings.rate_limit_max_requests = max_req
        mock_settings.rate_limit_window_seconds = 60

        for _ in range(max_req + 5):
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert "x-ratelimit-limit" not in resp.headers


async def test_preview_escapes_html_to_prevent_xss(
    client: AsyncClient,
    fake_redis: FakeRedis,
) -> None:
    malicious_url = 'https://example.com/<script>alert("xss")</script>'
    fake_redis.set("short:XSSCODE", malicious_url)

    malicious_og = OGData(
        title='<script>alert("xss")</script>',
        description='<img src=x onerror=alert("xss")>',
        site_name="<script>evil</script>",
        image=None,
    )
    with patch("app.api.routes.fetch_og_data", new_callable=AsyncMock, return_value=malicious_og):
        preview_resp = await client.get("/!XSSCODE")
    assert preview_resp.status_code == 200
    assert "<script>" not in preview_resp.text
    assert "&lt;script&gt;" in preview_resp.text


async def test_stats_returns_click_count(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["short_code"]

    for _ in range(3):
        await client.get(f"/{code}", follow_redirects=False)

    stats_resp = await client.get(f"/stats/{code}")
    assert stats_resp.status_code == 200
    body = stats_resp.json()
    assert body["total_clicks"] == 3
    assert body["clicks_24h"] == 3
    assert body["clicks_7d"] == 3


async def test_stats_returns_404_for_unknown_code(client: AsyncClient) -> None:
    resp = await client.get("/stats/nonexistent")
    assert resp.status_code == 404


async def test_stats_tracks_referrer(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com"})
    code = resp.json()["short_code"]

    await client.get(
        f"/{code}",
        headers={"Referer": "https://twitter.com/post/123"},
        follow_redirects=False,
    )

    stats_resp = await client.get(f"/stats/{code}")
    assert stats_resp.status_code == 200
    body = stats_resp.json()
    referrers = body["top_referrers"]
    assert len(referrers) >= 1
    assert referrers[0]["domain"] == "twitter.com"
    assert referrers[0]["clicks"] == 1


async def test_create_url_with_ttl(
    client: AsyncClient,
    fake_redis: FakeRedis,
) -> None:
    resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/ttl", "ttl_seconds": 60},
    )
    assert resp.status_code == 200
    code = resp.json()["short_code"]

    # URL resolves normally
    redirect_resp = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_resp.status_code == 301

    # Redis TTL is set on the key
    remaining = fake_redis.ttl(f"short:{code}")
    assert remaining > 0
    assert remaining <= 60

    # meta hash stores expires_at
    assert fake_redis.hget(f"meta:{code}", "expires_at") is not None


async def test_create_url_without_ttl_has_no_expiration(
    client: AsyncClient,
    fake_redis: FakeRedis,
) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com/no-ttl"})
    assert resp.status_code == 200
    code = resp.json()["short_code"]

    # No TTL set — key has no expiry
    assert fake_redis.ttl(f"short:{code}") == -1
    assert fake_redis.hget(f"meta:{code}", "expires_at") is None


async def test_expired_url_returns_404(
    client: AsyncClient,
    fake_redis: FakeRedis,
) -> None:
    resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/expire", "ttl_seconds": 60},
    )
    assert resp.status_code == 200
    code = resp.json()["short_code"]

    # Simulate expiration by setting expiry to the past
    fake_redis._expiry[f"short:{code}"] = time.time() - 1

    redirect_resp = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_resp.status_code == 404


async def test_preview_shows_og_card(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com/og"})
    code = resp.json()["short_code"]

    og_html = (
        "<html><head>"
        '<meta property="og:title" content="Test Title">'
        '<meta property="og:description" content="Test Description">'
        '<meta property="og:site_name" content="Example Site">'
        "</head><body></body></html>"
    )

    mock_response = MagicMock()
    mock_response.text = og_html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.og_service.httpx.AsyncClient", return_value=mock_client):
        preview_resp = await client.get(f"/!{code}")

    assert preview_resp.status_code == 200
    assert "Test Title" in preview_resp.text
    assert "Test Description" in preview_resp.text
    assert "Example Site" in preview_resp.text


async def test_preview_graceful_fallback_on_og_failure(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com/fail"})
    code = resp.json()["short_code"]

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.og_service.httpx.AsyncClient", return_value=mock_client):
        preview_resp = await client.get(f"/!{code}")

    assert preview_resp.status_code == 200
    assert "https://example.com/fail" in preview_resp.text
    assert "No description available" in preview_resp.text


async def test_preview_caches_og_data(client: AsyncClient) -> None:
    resp = await client.post("/shorten", json={"url": "https://example.com/cache"})
    code = resp.json()["short_code"]

    og_html = (
        '<html><head><meta property="og:title" content="Cached Title"></head><body></body></html>'
    )

    mock_response = MagicMock()
    mock_response.text = og_html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_cls = MagicMock(return_value=mock_client)

    with patch("app.services.og_service.httpx.AsyncClient", mock_cls):
        await client.get(f"/!{code}")
        await client.get(f"/!{code}")

    # httpx.AsyncClient should only be instantiated once (second call uses cache)
    assert mock_cls.call_count == 1
