# Cache operations

Cache invalidation is triggered after a successful write. The worker records the object version before deleting stale entries.

Eviction uses a bounded least-recently-used queue. A cache miss is safe and falls back to the source of truth.
