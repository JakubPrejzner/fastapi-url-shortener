from __future__ import annotations

import logging
from collections.abc import Generator
from typing import TYPE_CHECKING, cast

import redis

from app.core.config import settings

if TYPE_CHECKING:
    _StrRedis = redis.Redis[str]
else:
    _StrRedis = redis.Redis

logger = logging.getLogger(__name__)

_pool: redis.ConnectionPool | None = None


def _get_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        logger.info(
            "Redis connection pool created: %s:%s/%s",
            settings.redis_host,
            settings.redis_port,
            settings.redis_db,
        )
    return _pool


def get_redis_client() -> Generator[_StrRedis, None, None]:
    """Yield a Redis client from the connection pool."""
    client = cast(_StrRedis, redis.Redis(connection_pool=_get_pool()))
    try:
        yield client
    finally:
        client.close()
