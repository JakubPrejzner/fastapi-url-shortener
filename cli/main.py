from __future__ import annotations

import sys

import click
import redis
from pydantic import HttpUrl, ValidationError

from app.core.config import settings
from app.services.url_service import (
    create_short_url,
    delete_short_url,
    update_short_url,
)


def _get_redis() -> redis.Redis[str]:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def _validate_url(url: str) -> str:
    """Validate *url* as an HTTP(S) URL or raise click.BadParameter."""
    try:
        validated = HttpUrl(url)
    except ValidationError:
        raise click.BadParameter(f"'{url}' is not a valid HTTP URL.") from None
    return str(validated)


@click.group()
def cli() -> None:
    """URL Shortener CLI — manage short URLs."""


@cli.command()
@click.argument("url")
@click.option("--ttl", type=int, default=None, help="TTL in seconds for the short URL.")
def add(url: str, ttl: int | None) -> None:
    """Shorten a URL and print the short link."""
    url = _validate_url(url)
    r = _get_redis()
    code = create_short_url(r, url, ttl_seconds=ttl)
    click.echo(f"{settings.base_url}/{code}")


@cli.command()
@click.argument("short_code")
@click.argument("new_url")
def update(short_code: str, new_url: str) -> None:
    """Update the target URL behind SHORT_CODE."""
    new_url = _validate_url(new_url)
    r = _get_redis()
    try:
        update_short_url(r, short_code, new_url)
    except Exception:
        click.echo(f"Error: short code '{short_code}' not found.", err=True)
        sys.exit(1)
    click.echo(f"Updated {short_code} -> {new_url}")


@cli.command()
@click.argument("short_code")
def delete(short_code: str) -> None:
    """Delete a short URL entry."""
    r = _get_redis()
    try:
        delete_short_url(r, short_code)
    except Exception:
        click.echo(f"Error: short code '{short_code}' not found.", err=True)
        sys.exit(1)
    click.echo(f"Deleted {short_code}")


if __name__ == "__main__":
    cli()
