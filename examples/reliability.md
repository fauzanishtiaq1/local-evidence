# Reliability runbook

Retry backoff uses exponential delays with jitter. The client caps attempts and preserves the original error in its event record.

Circuit breakers open after a rolling failure threshold and close only after a probe succeeds.
