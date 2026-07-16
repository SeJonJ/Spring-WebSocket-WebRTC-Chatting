# ChatForYou Realtime Media Safety Protocol

This protocol applies to signaling, media-session lifecycle, room recovery, and synchronized web/desktop media behavior. Implementation is blocked until a current-cycle review document under `plan_docs/02-design/reviews/` binds this domain and records both rounds.

## Round 1: Flow Correctness

- Verify offer, answer, and candidate ordering across client, server, and media server.
- Trace room ownership, authenticated session attribution, and every state transition.
- Check duplicate, delayed, reordered, and missing messages.
- Confirm schema and behavior compatibility for existing clients.
- Record reviewed files and P0/P1/P2 findings.

## Round 2: Failure And Lifecycle

- Verify concurrent join, duplicate offer, disconnect, reconnect, and server restart behavior.
- Prove media resources are released on every terminal path.
- Test idempotency, bounded retries, and long-lived quiet calls.
- Do not infer call failure from signaling-channel idleness; media and signaling use different traffic paths.
- Cross-check client timeouts against server settings and reject large unexplained mismatches.
- Verify web source changes are synchronized to desktop only through the documented sync workflow.

## Decision

- `APPROVED`: no unresolved P0/P1.
- `APPROVED_WITH_RISK`: remaining P1 has explicit user acceptance.
- `BLOCKED`: any P0 or unaccepted P1.
- A principle-level defect cannot be downgraded because it is central to an existing design.
