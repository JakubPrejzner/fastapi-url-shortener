from __future__ import annotations

import logging
import secrets
import string
import time
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import redis

from app.core.config import settings
from app.core.exceptions import ShortCodeCollision, ShortCodeNotFound
from app.models.schemas import ReferrerInfo, StatsResponse

logger = logging.getLogger(__name__)

# Redis key scheme:
#   short:{code}  -> original URL
#   url:{url}     -> short code  (reverse index for deduplication)
#   clicks:{code} -> sorted set of click UUIDs scored by timestamp
#   stats:{code}  -> hash with total, last_clicked_at, ref:{domain} counters
#   meta:{code}   -> hash with expires_at
_PREFIX_SHORT = "short:"
_PREFIX_URL = "url:"

_MAX_GENERATION_ATTEMPTS = 100


def _generate_code(length: int | None = None) -> str:
    length = length or settings.short_url_max_len
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_short_url(
    r: redis.Redis[str],
    original_url: str,
    ttl_seconds: int | None = None,
) -> str:
    """Return existing or newly generated short code for *original_url*."""
    existing_code = r.get(f"{_PREFIX_URL}{original_url}")
    if existing_code is not None:
        logger.debug("URL already shortened: %s -> %s", original_url, existing_code)
        return existing_code

    for _ in range(_MAX_GENERATION_ATTEMPTS):
        code = _generate_code()
        # SET NX ensures atomicity — only one writer wins the race.
        if r.set(f"{_PREFIX_SHORT}{code}", original_url, nx=True, ex=ttl_seconds):
            r.set(f"{_PREFIX_URL}{original_url}", code)
            if ttl_seconds is not None:
                expires_at = datetime.now(tz=UTC) + timedelta(seconds=ttl_seconds)
                r.hset(f"meta:{code}", "expires_at", expires_at.isoformat())
            logger.info("Created short URL: %s -> %s", code, original_url)
            return code

    raise ShortCodeCollision()


def resolve_short_url(
    r: redis.Redis[str],
    code: str,
    referer: str | None = None,
) -> str:
    """Resolve *code* to the original URL or raise 404."""
    url: str | None = r.get(f"{_PREFIX_SHORT}{code}")
    if url is None:
        raise ShortCodeNotFound(code)

    # Record click analytics
    now = time.time()
    click_id = str(uuid.uuid4())
    r.zadd(f"clicks:{code}", {click_id: now})
    r.hincrby(f"stats:{code}", "total", 1)
    r.hset(f"stats:{code}", "last_clicked_at", datetime.now(tz=UTC).isoformat())

    if referer:
        domain = urlparse(referer).netloc
        if domain:
            r.hincrby(f"stats:{code}", f"ref:{domain}", 1)

    return url


def get_url_stats(r: redis.Redis[str], code: str) -> StatsResponse:
    """Return click analytics for *code*."""
    original_url: str | None = r.get(f"{_PREFIX_SHORT}{code}")
    if original_url is None:
        raise ShortCodeNotFound(code)

    total_clicks = int(r.hget(f"stats:{code}", "total") or 0)

    now = time.time()
    clicks_24h = r.zcount(f"clicks:{code}", now - 86400, "+inf")
    clicks_7d = r.zcount(f"clicks:{code}", now - 604800, "+inf")

    all_stats: dict[str, str] = r.hgetall(f"stats:{code}") or {}
    referrers: list[ReferrerInfo] = []
    for key, value in all_stats.items():
        if key.startswith("ref:"):
            referrers.append(ReferrerInfo(domain=key[4:], clicks=int(value)))
    referrers.sort(key=lambda x: x.clicks, reverse=True)

    last_clicked_at_raw = all_stats.get("last_clicked_at")
    last_clicked_at = datetime.fromisoformat(last_clicked_at_raw) if last_clicked_at_raw else None

    # TTL / expiration info
    expires_at_raw = r.hget(f"meta:{code}", "expires_at")
    expires_at = datetime.fromisoformat(expires_at_raw) if expires_at_raw else None

    raw_ttl = r.ttl(f"{_PREFIX_SHORT}{code}")
    ttl_remaining = raw_ttl if raw_ttl > 0 else None

    return StatsResponse(
        code=code,
        original_url=original_url,
        total_clicks=total_clicks,
        clicks_24h=clicks_24h,
        clicks_7d=clicks_7d,
        top_referrers=referrers[:5],
        created_at=None,
        last_clicked_at=last_clicked_at,
        expires_at=expires_at,
        ttl_remaining=ttl_remaining,
    )


def update_short_url(r: redis.Redis[str], code: str, new_url: str) -> None:
    """Point *code* at a different URL. Raises 404 if code doesn't exist."""
    old_url: str | None = r.get(f"{_PREFIX_SHORT}{code}")
    if old_url is None:
        raise ShortCodeNotFound(code)

    r.delete(f"{_PREFIX_URL}{old_url}")
    r.set(f"{_PREFIX_SHORT}{code}", new_url)
    r.set(f"{_PREFIX_URL}{new_url}", code)
    logger.info("Updated short URL: %s -> %s (was %s)", code, new_url, old_url)


def delete_short_url(r: redis.Redis[str], code: str) -> None:
    """Remove a short URL entry. Raises 404 if code doesn't exist."""
    old_url: str | None = r.get(f"{_PREFIX_SHORT}{code}")
    if old_url is None:
        raise ShortCodeNotFound(code)

    r.delete(f"{_PREFIX_SHORT}{code}")
    r.delete(f"{_PREFIX_URL}{old_url}")
    logger.info("Deleted short URL: %s (was -> %s)", code, old_url)
