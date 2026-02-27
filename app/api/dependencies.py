from typing import TYPE_CHECKING, Annotated

import redis
from fastapi import Depends

from app.db.redis_client import get_redis_client

if TYPE_CHECKING:
    RedisClient = Annotated[redis.Redis[str], Depends(get_redis_client)]
else:
    RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
