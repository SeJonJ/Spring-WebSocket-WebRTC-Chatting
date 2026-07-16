# verification-protocol.md

Gate policy for L1/L2/L3 changes. Concrete commands come from
`profile.verification` and `scripts/verify-changes.sh`; this document defines
the policy that hooks enforce.

| Level | Checks | Mode |
|-------|--------|------|
| L1 | syntax | advisory |
| L2 | build, test, lint | block |
| L3 | build, test, lint, review | block |

## L3 review

L3 changes require an independent review before merge. The reviewer runtime is
resolved by `sage doctor` from `profile.options.cross_model`:

- cross_model off → clean-context review in the same runtime.
- cross_model on + opposite runtime reachable → opposite-runtime review.
- cross_model on + opposite runtime unreachable → clean-context fallback
  (degraded; surfaced by `sage doctor`).

How an L3 change is matched to its review document is a project decision
(`profile.risk.l3_review_strategy`). Until selected, `pre-implementation-gate`
blocks L3 changes (safe default).

## Acceptance evidence

Deterministic commands prove that configured checks ran; they do not prove every
explicit user requirement was satisfied. When `profile.verification.acceptance`
is enabled:

- Phase 01 must define an acceptance matrix for explicit user requirements.
- Phase 03 maps implementation and tests to those acceptance IDs.
- Phase 04 records `PASS`, `FAIL`, `NOT TESTED`, or `N/A` for each item with
  concrete evidence.
- Phase 05 treats required `FAIL` or `NOT TESTED` items as blocking.
- Phase 06 may warn or block, depending on `report_gate_enforce`, if Phase 04
  evidence is missing or unresolved.
