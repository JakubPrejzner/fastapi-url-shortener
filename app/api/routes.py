import html
import logging
from urllib.parse import urlparse

import redis
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import RedisClient
from app.core.config import settings
from app.models.schemas import HealthResponse, ShortenRequest, ShortenResponse, StatsResponse
from app.services.og_service import fetch_og_data
from app.services.url_service import create_short_url, get_url_stats, resolve_short_url

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(r: RedisClient) -> HealthResponse:
    try:
        redis_ok = r.ping()
    except redis.RedisError:
        redis_ok = False
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis="up" if redis_ok else "down",
    )


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_200_OK,
)
def shorten(body: ShortenRequest, r: RedisClient) -> ShortenResponse:
    original_url = str(body.url)
    code = create_short_url(r, original_url, ttl_seconds=body.ttl_seconds)
    return ShortenResponse(
        short_url=f"{settings.base_url}/{code}",
        short_code=code,
        original_url=original_url,
    )


@router.get("/stats/{code}", response_model=StatsResponse)
def stats(code: str, r: RedisClient) -> StatsResponse:
    return get_url_stats(r, code)


@router.get("/!{short_code}")
async def preview(short_code: str, r: RedisClient) -> HTMLResponse:
    original_url = resolve_short_url(r, short_code)
    og = await fetch_og_data(original_url, r)

    total_clicks = int(r.hget(f"stats:{short_code}", "total") or 0)
    domain = urlparse(original_url).netloc

    escaped_url = html.escape(original_url)
    escaped_title = html.escape(og.title or original_url)
    escaped_desc = html.escape(og.description or "No description available")
    escaped_site_name = html.escape(og.site_name or domain)

    og_image_html = ""
    if og.image:
        escaped_image = html.escape(og.image)
        og_image_html = f'<img class="card-image" src="{escaped_image}" alt="">'

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Preview \u2014 {html.escape(short_code)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: #1a1a2e;
            border: 1px solid #16213e;
            border-radius: 12px;
            max-width: 600px;
            width: 100%;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }}
        .card-image {{
            width: 100%;
            max-height: 300px;
            object-fit: cover;
        }}
        .card-body {{ padding: 24px; }}
        .site-name {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6c63ff;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-size: 20px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 12px;
            line-height: 1.3;
        }}
        .card-title a {{ color: #ffffff; text-decoration: none; }}
        .card-title a:hover {{ color: #6c63ff; }}
        .card-desc {{
            font-size: 14px;
            color: #a0a0a0;
            line-height: 1.6;
            margin-bottom: 16px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .card-footer {{
            padding: 16px 24px;
            background: #16213e;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
        }}
        .card-url {{
            color: #6c63ff;
            text-decoration: none;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 70%;
        }}
        .card-stats {{ color: #666; }}
    </style>
</head>
<body>
    <div class="card">
        {og_image_html}
        <div class="card-body">
            <div class="site-name">{escaped_site_name}</div>
            <h1 class="card-title"><a href="{escaped_url}">{escaped_title}</a></h1>
            <p class="card-desc">{escaped_desc}</p>
        </div>
        <div class="card-footer">
            <a class="card-url" href="{escaped_url}">\U0001f517 {escaped_url}</a>
            <span class="card-stats">\U0001f4ca {total_clicks} clicks</span>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=content)


@router.get("/{short_code}")
def redirect(short_code: str, r: RedisClient, request: Request) -> RedirectResponse:
    referer = request.headers.get("referer")
    original_url = resolve_short_url(r, short_code, referer=referer)
    return RedirectResponse(url=original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)
