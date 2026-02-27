import pytest

from app.core.exceptions import ShortCodeNotFound
from app.services.url_service import (
    create_short_url,
    delete_short_url,
    resolve_short_url,
    update_short_url,
)
from tests.conftest import FakeRedis


@pytest.fixture
def r() -> FakeRedis:
    return FakeRedis()


def test_create_and_resolve(r: FakeRedis) -> None:
    code = create_short_url(r, "https://example.com")  # type: ignore[arg-type]
    assert isinstance(code, str)
    assert len(code) > 0
    assert resolve_short_url(r, code) == "https://example.com"  # type: ignore[arg-type]


def test_create_is_idempotent(r: FakeRedis) -> None:
    c1 = create_short_url(r, "https://example.com")  # type: ignore[arg-type]
    c2 = create_short_url(r, "https://example.com")  # type: ignore[arg-type]
    assert c1 == c2


def test_resolve_missing_raises(r: FakeRedis) -> None:
    with pytest.raises(ShortCodeNotFound):
        resolve_short_url(r, "missing")  # type: ignore[arg-type]


def test_update(r: FakeRedis) -> None:
    code = create_short_url(r, "https://old.com")  # type: ignore[arg-type]
    update_short_url(r, code, "https://new.com")  # type: ignore[arg-type]
    assert resolve_short_url(r, code) == "https://new.com"  # type: ignore[arg-type]


def test_update_missing_raises(r: FakeRedis) -> None:
    with pytest.raises(ShortCodeNotFound):
        update_short_url(r, "missing", "https://x.com")  # type: ignore[arg-type]


def test_delete(r: FakeRedis) -> None:
    code = create_short_url(r, "https://example.com")  # type: ignore[arg-type]
    delete_short_url(r, code)  # type: ignore[arg-type]
    with pytest.raises(ShortCodeNotFound):
        resolve_short_url(r, code)  # type: ignore[arg-type]


def test_delete_missing_raises(r: FakeRedis) -> None:
    with pytest.raises(ShortCodeNotFound):
        delete_short_url(r, "missing")  # type: ignore[arg-type]
