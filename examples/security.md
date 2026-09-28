# Security operations

Access token rotation uses overlapping validity windows so active clients can refresh safely. Revoked tokens are rejected at the gateway.

Audit records omit secret values and retain actor, action, and timestamp fields.
