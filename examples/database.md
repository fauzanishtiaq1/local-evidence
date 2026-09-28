# Database operations

Schema migration is applied in an isolated transaction with a recorded version. Backward-compatible columns are deployed before readers change.

The rollback procedure restores the prior version and verifies row counts.
