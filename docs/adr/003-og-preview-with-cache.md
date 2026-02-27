# ADR-003: OpenGraph Preview With Cache

## Status
Accepted

## Context
The preview endpoint (`/!{code}`) originally returned a plain redirect target. Users sharing shortened links in chat or documentation benefit from seeing the destination's title, description, and image before clicking, similar to how Slack and Discord render link previews.

Fetching OpenGraph metadata requires an outbound HTTP request to the target URL, which introduces latency and a dependency on third-party availability.

## Decision
Fetch OpenGraph meta tags (`og:title`, `og:description`, `og:image`, `og:site_name`) from the destination URL using `httpx.AsyncClient` with a 3-second timeout. Fall back to `<title>` and `<meta name="description">` when OG tags are absent. Cache the parsed result in Redis with a 1-hour TTL (`og:{url} -> JSON`).

If the fetch fails for any reason (timeout, DNS failure, non-2xx response), return a graceful fallback card showing the raw URL and "No description available" rather than an error page.

## Consequences
### Positive
- Rich preview cards improve user trust and click-through context.
- The 1-hour cache eliminates redundant outbound requests; repeated previews of the same link are served from Redis in microseconds.
- Async fetch keeps the event loop unblocked during the outbound request.
- Graceful degradation means the preview endpoint never returns an error to the user.

### Negative
- First preview request for a given URL incurs 1-3 seconds of latency while fetching from the target.
- OG data may become stale within the 1-hour cache window. An explicit cache-bust mechanism is not yet implemented.
- Some sites block bot user agents or serve different content, which may result in missing or inaccurate metadata.
