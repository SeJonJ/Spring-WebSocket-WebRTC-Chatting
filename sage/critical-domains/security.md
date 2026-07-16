# ChatForYou Security Domain Protocol

This protocol applies to authentication, token lifecycle, credentials, transport keys, and authorization boundaries.

- Trace issuer, subject, audience, expiry, refresh, revocation, and room/user ownership.
- Never expose credential material in source, logs, fixtures, generated artifacts, or review evidence.
- Verify authorization at the server boundary rather than relying on client state.
- Cover replay, stale token, concurrent refresh, logout, and partial-failure paths.
- Require current-cycle two-round L3 review evidence before implementation.
