---
id: convention-checker
kind: agent
# CORE roster (neutral, generic helper — one instance, stack from profile).
---
## intent
Verification helper that checks recently changed files (via git diff) against
the convention docs declared in `profile.conventions`, and reports violations
with fix guidance.

## advisory_scope
- owns: (nothing — verification helper, read-only over the diff)
- role_boundary: does not modify code; reports convention violations only
- uses: git diff; convention docs declared in profile.conventions
- input_scope: changed files (git diff)
- convention_doc: (per profile.conventions — backend/frontend/etc.)
- self_overlay: unsupported; this unverified CORE agent is not in `COMPOSE_ALLOWED`

## runtime_bindings
- model / effort: (from profile.team.core.convention-checker.runtime; unset model = host CLI
  default, unset effort = high). claude host only — injected into the agent frontmatter by
  `sage install`; re-run `sage install --force` after changing them.
- claims/allowlist are auto-derived into {id}.claims.yml by reverse_extract
