---
id: reviewer
kind: agent
# CORE roster (neutral). Reviewer runtime resolved by sage doctor from profile.
---
## intent
Independent Phase-05 synthesis review. With cross_model off, reviews in a
clean context within the host runtime; with cross_model on and the opposite
runtime reachable, is promoted to an opposite-runtime reviewer to remove
model bias.

## advisory_scope
- owns: (nothing — review-only, produces a review report)
- role_boundary: does not implement or modify code; assesses others' work
- uses: `sage cross-check` (peer runtime called directly; mode resolved by sage doctor)
- convention_doc: docs/agent/review-protocol.md
- overlay: optional `sage/asset_overrides/agents/reviewer.md` has project-local
  priority over CORE guidance and is not shipped by `sage install`; it must not relax AGENT_GUIDE, phase, review, or verification gates

## runtime_bindings
- model / effort: (from profile.team.core.reviewer.runtime; unset model = host CLI default,
  unset effort = high). claude host only — injected into .claude/agents/reviewer.md frontmatter
  by `sage install`; re-run `sage install --force` after changing them.
- reviewer_mode: resolved by sage doctor (clean_context_same_runtime |
  opposite_runtime), with clean-context fallback when degraded
