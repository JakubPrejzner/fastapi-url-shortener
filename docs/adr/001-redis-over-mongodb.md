# ADR-001: Redis Over MongoDB

## Status
Accepted

## Context
The URL shortener needs a datastore for short code mappings, click analytics, and optional TTL-based expiration. Requirements: sub-millisecond lookups on redirect (the hot path), atomic operations for concurrent writes, native TTL support for expiring links, and simple deployment with minimal operational overhead.

MongoDB was considered as an alternative given its flexibility with document schemas and built-in TTL indexes.

## Decision
Use Redis as the sole data store. Short URL mappings are stored as simple key-value pairs (`short:{code} -> url`), with a reverse index (`url:{url} -> code`) for deduplication. Click analytics use sorted sets scored by timestamp, enabling efficient time-windowed queries (e.g., clicks in the last 24h) via `ZCOUNT`. Atomic `SET NX` provides collision-free code generation without application-level locking, and `INCR`/`HINCRBY` handle counters without read-modify-write cycles.

Redis's native key expiration eliminates the need for a background cleanup job for TTL-based links.

## Consequences
### Positive
- O(1) lookups on the redirect path keep tail latency low.
- Atomic primitives (`SET NX`, `INCR`, `ZADD`) simplify concurrent access patterns.
- Native TTL expiration requires zero application code for link cleanup.
- Single-binary deployment; the same instance serves both data storage and rate limiting.

### Negative
- All data is in-memory, limiting dataset size to available RAM. Mitigated by RDB/AOF persistence and the inherently small size of URL mapping data.
- No support for complex queries or ad-hoc reporting. If advanced analytics are needed later, an event pipeline to a secondary store would be required.
- No built-in full-text search or relational joins, which would matter if the product evolved toward a link management platform.
