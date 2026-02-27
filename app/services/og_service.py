from __future__ import annotations

import logging

import httpx
import redis
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OGData(BaseModel):
    title: str | None = None
    description: str | None = None
    image: str | None = None
    site_name: str | None = None


_USER_AGENT = "Mozilla/5.0 (compatible; URLShortenerBot/1.0)"


def _get_meta_property(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    if tag:
        content = tag.get("content")
        if content and isinstance(content, str):
            return content
    return None


async def fetch_og_data(url: str, r: redis.Redis[str]) -> OGData:
    """Fetch OpenGraph metadata for *url* with Redis caching."""
    # Check cache
    cached = r.get(f"og:{url}")
    if cached is not None:
        try:
            return OGData.model_validate_json(cached)
        except Exception:
            logger.debug("Failed to parse cached OG data for %s", url)

    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        og_title = _get_meta_property(soup, "og:title")
        og_desc = _get_meta_property(soup, "og:description")
        og_image = _get_meta_property(soup, "og:image")
        og_site_name = _get_meta_property(soup, "og:site_name")

        # Fallbacks
        if not og_title:
            title_tag = soup.find("title")
            if title_tag:
                og_title = title_tag.get_text(strip=True)

        if not og_desc:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                desc_content = meta_desc.get("content")
                if desc_content and isinstance(desc_content, str):
                    og_desc = desc_content

        data = OGData(
            title=og_title,
            description=og_desc,
            image=og_image,
            site_name=og_site_name,
        )
    except Exception:
        logger.debug("Failed to fetch OG data for %s", url)
        data = OGData()

    # Cache result (1 hour)
    try:
        r.set(f"og:{url}", data.model_dump_json(), ex=3600)
    except Exception:
        logger.debug("Failed to cache OG data for %s", url)

    return data
