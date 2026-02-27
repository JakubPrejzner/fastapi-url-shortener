from __future__ import annotations

from typing import TYPE_CHECKING, cast

import redis
from fastapi import FastAPI

from app.api.middleware import RateLimitMiddleware, RequestIDMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.redis_client import _get_pool

if TYPE_CHECKING:
    _StrRedis = redis.Redis[str]
else:
    _StrRedis = redis.Redis


def create_app() -> FastAPI:
    setup_logging(settings)

    app = FastAPI(title="URL Shortener", version="1.0.0")
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.include_router(router)

    def _redis_factory() -> _StrRedis:
        return cast(_StrRedis, redis.Redis(connection_pool=_get_pool()))

    app.state.redis_factory = _redis_factory

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
