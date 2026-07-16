# ChatForYou Game Domain Protocol

This protocol applies to CatchMind and future ChatForYou game features across
server state, realtime messages, web clients, and desktop synchronization.

## Rules And State

- Define the authoritative server state, legal transitions, timers, and scoring rules.
- Validate player identity, room membership, turn ownership, and answer permissions.
- Handle duplicate, delayed, reordered, and missing realtime messages deterministically.
- Preserve backward compatibility when extending game message schemas.

## Fairness And Lifecycle

- Test join, leave, reconnect, timeout, host migration, and room termination paths.
- Prevent clients from choosing protected values or overriding authoritative outcomes.
- Verify concurrent answers and timer expiry produce one deterministic result.
- Synchronize web changes to desktop only through the documented sync workflow.

## Decision

- `APPROVED`: no unresolved P0/P1.
- `APPROVED_WITH_RISK`: remaining P1 has explicit user acceptance and follow-up evidence.
- `BLOCKED`: any P0 or unaccepted P1.
