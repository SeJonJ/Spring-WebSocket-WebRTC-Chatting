# ChatForYou Recording Lifecycle Protocol

This protocol applies to recording start and stop, partial markers, upload,
download, cleanup, recovery, and media-resource ownership.

## Lifecycle And State

- Define every recording state transition and the owner allowed to trigger it.
- Verify start, stop, retry, timeout, disconnect, shutdown, and restart paths.
- Keep Redis markers, room state, persisted metadata, and file state consistent.
- Require idempotency for duplicate events, cleanup retries, and recovery work.

## Data And Resource Safety

- Never expose recording files or download tokens without server-side authorization.
- Prove temporary and partial files are retained or deleted by an explicit policy.
- Verify media endpoints, streams, files, and markers are released on all terminal paths.
- Test concurrent stop, upload completion, cleanup, and room recovery ordering.

## Decision

- `APPROVED`: no unresolved P0/P1.
- `APPROVED_WITH_RISK`: remaining P1 has explicit user acceptance and follow-up evidence.
- `BLOCKED`: any P0 or unaccepted P1.
