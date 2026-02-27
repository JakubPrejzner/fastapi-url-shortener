# ADR-004: Rate Limiting Strategy

## Status
Accepted

## Context
A public URL shortening API is vulnerable to abuse: automated link generation, redirect-based DDoS amplification, and scraping of analytics endpoints. Rate limiting is required. Three approaches were evaluated: (a) nginx-level `limit_req`, (b) application-level middleware backed by Redis, (c) a dedicated API gateway.

## Decision
Implement application-level rate limiting as Starlette middleware using a sliding window counter in Redis. Each request increments a per-IP key (`ratelimit:{ip}`) with `INCR` and sets a TTL with `EXPIRE` on first access. When the counter exceeds the configured threshold, the middleware short-circuits with a 429 response.

Standard rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`) are included on every response. The `/health` endpoint is exempt to avoid interfering with orchestrator probes. All parameters are configurable via environment variables (`RATE_LIMIT_ENABLED`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`).

## Consequences
### Positive
- Leverages the existing Redis instance, adding no new infrastructure dependencies.
- Fully configurable and disableable without redeployment (environment variables).
- Runs in-process, making it straightforward to test with the existing test suite and `FakeRedis`.
- Standard headers let well-behaved clients implement backoff automatically.

### Negative
- Adds a Redis round-trip to every non-health request. The overhead is minimal since Redis is already in the request path, but it is nonzero.
- IP-based identification can be circumvented by rotating proxies. Acceptable at this scale; token-based limiting would be needed for a multi-tenant SaaS product.
- Less performant than nginx-level limiting for extreme traffic volumes, where rejecting requests before they reach the application layer is preferable.
