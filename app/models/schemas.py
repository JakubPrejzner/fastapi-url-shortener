from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    ttl_seconds: int | None = None


class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    original_url: str


class HealthResponse(BaseModel):
    status: str
    redis: str


class ReferrerInfo(BaseModel):
    domain: str
    clicks: int


class StatsResponse(BaseModel):
    code: str
    original_url: str
    total_clicks: int
    clicks_24h: int
    clicks_7d: int
    top_referrers: list[ReferrerInfo]
    created_at: datetime | None
    last_clicked_at: datetime | None
    expires_at: datetime | None = None
    ttl_remaining: int | None = None
