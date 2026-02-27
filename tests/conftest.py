"""Shared fixtures: fake Redis and FastAPI test client."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.redis_client import get_redis_client
from app.main import create_app


class FakePipeline:
    """Fake Redis pipeline that batches commands."""

    def __init__(self, fake_redis: FakeRedis) -> None:
        self._redis = fake_redis
        self._commands: list[tuple[str, tuple[Any, ...]]] = []

    def incr(self, key: str) -> FakePipeline:
        self._commands.append(("incr", (key,)))
        return self

    def ttl(self, key: str) -> FakePipeline:
        self._commands.append(("ttl", (key,)))
        return self

    def execute(self) -> list[Any]:
        results: list[Any] = []
        for cmd, args in self._commands:
            results.append(getattr(self._redis, cmd)(*args))
        self._commands.clear()
        return results


class FakeRedis:
    """Minimal dict-backed Redis stand-in for tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        self._ttls: dict[str, int] = {}
        self._expiry: dict[str, float] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sorted_sets: dict[str, list[tuple[float, str]]] = {}

    def _is_expired(self, key: str) -> bool:
        if key in self._expiry and time.time() >= self._expiry[key]:
            self._store.pop(key, None)
            del self._expiry[key]
            return True
        return False

    def get(self, key: str) -> str | None:
        self._is_expired(key)
        return self._store.get(key)

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        self._is_expired(key)
        if nx and key in self._store:
            return False
        self._store[key] = value
        if ex is not None:
            self._expiry[key] = time.time() + ex
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
            self._counters.pop(k, None)
            self._ttls.pop(k, None)
            self._expiry.pop(k, None)
        return count

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def incr(self, key: str) -> int:
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    def expire(self, key: str, seconds: int) -> bool:
        self._ttls[key] = seconds
        return True

    def ttl(self, key: str) -> int:
        if key in self._expiry:
            remaining = int(self._expiry[key] - time.time())
            if remaining <= 0:
                self._store.pop(key, None)
                self._expiry.pop(key, None)
                return -2
            return remaining
        return self._ttls.get(key, -1)

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    # --- Hash commands ---

    def hset(self, key: str, field: str, value: str) -> int:
        if key not in self._hashes:
            self._hashes[key] = {}
        is_new = field not in self._hashes[key]
        self._hashes[key][field] = str(value)
        return 1 if is_new else 0

    def hget(self, key: str, field: str) -> str | None:
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        if key not in self._hashes:
            self._hashes[key] = {}
        current = int(self._hashes[key].get(field, "0"))
        new_val = current + amount
        self._hashes[key][field] = str(new_val)
        return new_val

    # --- Sorted-set commands ---

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        if key not in self._sorted_sets:
            self._sorted_sets[key] = []
        added = 0
        for member, score in mapping.items():
            self._sorted_sets[key].append((score, member))
            added += 1
        return added

    def zcount(self, key: str, min_score: float | str, max_score: float | str) -> int:
        if key not in self._sorted_sets:
            return 0
        count = 0
        for score, _member in self._sorted_sets[key]:
            min_ok = min_score == "-inf" or score >= float(min_score)
            max_ok = max_score == "+inf" or score <= float(max_score)
            if min_ok and max_ok:
                count += 1
        return count


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture()
async def client(fake_redis: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    def _override() -> Generator[Any, None, None]:
        yield fake_redis

    app.dependency_overrides[get_redis_client] = _override
    app.state.redis_factory = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
