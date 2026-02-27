# ADR-002: Idempotent URL Shortening

## Status
Accepted

## Context
Shortening the same URL multiple times must return the same short code. This prevents database bloat and gives clients a stable, predictable link for any given input. Two approaches were considered: (a) generate a random code then check for an existing mapping on each request, requiring an extra read before every write, or (b) maintain a reverse index so that repeat submissions resolve instantly.

## Decision
Maintain a reverse index in Redis (`url:{original_url} -> code`) alongside the forward mapping (`short:{code} -> url`). On each shorten request, the service first checks the reverse index. If the URL has already been shortened, the existing code is returned immediately with no write. New URLs get a cryptographically random code via `secrets.choice`, written atomically with `SET NX` to handle concurrent generation of the same code.

The collision retry loop (up to 100 attempts) handles the rare case where two different URLs generate the same random code simultaneously.

## Consequences
### Positive
- Idempotency is a single O(1) read, not a table scan or secondary index query.
- No duplicate entries accumulate over time, keeping the dataset compact.
- Clients can safely retry without side effects.

### Negative
- The reverse index doubles the number of keys per URL. At the scale of a URL shortener this is negligible, but it would matter at billions of entries.
- Deleting or updating a short URL requires maintaining both indexes, adding a small amount of bookkeeping logic.
- Random code generation is not deterministic from the input URL, so the reverse index is essential rather than optional.
