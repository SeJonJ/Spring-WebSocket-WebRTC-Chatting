---
id: qa
kind: agent
# CORE roster (neutral). Paths come from profile, not this spec.
---
## intent
Test scenario design, integration tests, boundary-value tests, and HTTP-layer
tests. Verifies cases that component implementers tend to miss (concurrency,
auth, boundaries) from a user/attacker perspective.

## advisory_scope
- owns: test paths declared in `profile.components` (owns: ["**/test/**"])
- role_boundary: does not own production source; reviews and tests it. Runs
  after implementers' unit tests.
- uses: (qa skills declared in profile.team)
- convention_doc: AGENT_GUIDE.md
- self_overlay: unsupported; this gate-bearing CORE agent is not in `COMPOSE_ALLOWED`

## runtime_bindings
- model / effort: (from profile.team.core.qa.runtime; unset model = host CLI default,
  unset effort = high). claude host only — injected into .claude/agents/qa.md frontmatter
  by `sage install`; re-run `sage install --force` after changing them.
- claims/allowlist are auto-derived into {id}.claims.yml by reverse_extract
