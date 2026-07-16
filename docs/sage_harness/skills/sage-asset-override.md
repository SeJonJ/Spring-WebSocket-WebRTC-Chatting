---
id: sage-asset-override
kind: skill
# CORE skill (neutral). Project specifics come from the overlay files, not this spec.
# CORE framework bootstrap asset: hand-shipped by `sage install`, NOT manifest-tracked.
# The manifest/claims/validate loop is reserved for project-authored skills
# (spec + claims + render hash) created via the generate/extract flow.
---
## intent
Author a project-local overlay for an EXISTING CORE agent/skill through conversation:
show the current CORE base behavior, interview the desired local deviation, WARN (with
mandatory confirmation) if it looks like it relaxes a governance gate, then write
directly to sage/asset_overrides/{agents,skills}/<id>.md — a hand-authored file that
`sage install` never ships and `sage install --force` preserves (no `sage generate`
step). The overlay-authoring counterpart to /sage-asset (new assets) and
/sage-profile-modify (profile values).

## when_to_use
- After a retro/absorb proposal suggests an agent/skill-target learning to keep for this
  project without editing the CORE render (which --force would overwrite)
- When the user wants to customize a CORE roster agent (leader/implementer-a/implementer-b/
  qa/reviewer/convention-checker) or a CORE skill (sage-init/sage-cycle/sage-plan/
  sage-team/sage-review/sage-asset/sage-profile-modify) for THIS project only
- When the user says "/sage-asset-override", "오버레이 작성", "CORE 커스터마이즈"

## procedure
1. Read context: profile bootstrapped; the target CORE base spec
   (docs/sage_harness/{agents,skills}/<id>.md) or its render; AGENT_GUIDE.
2. Identify kind(agent|skill) + id — MUST be an existing CORE roster id. A new asset is
   /sage-asset's job (spec→generate), not an overlay → route there and stop.
3. Show the current CORE base content relevant to the requested change (so the user sees
   what the overlay adds on top of, not replaces).
4. Interview: what local deviation, and why (e.g. a retro pattern to stop recurring).
5. Draft the overlay text, then run the gate-relaxation check (sage.overlay_lint /
   `sage validate` surfaces it). If it looks like it relaxes AGENT_GUIDE/phase/review/
   verification, **require an explicit "yes" before writing** — never proceed silently
   (mirrors /sage-profile-modify's mandatory consequence warning).
6. Write sage/asset_overrides/{agents,skills}/<id>.md directly (no `sage generate`).
7. Re-validate: confirm the file exists and `sage validate` has no unresolved overlay
   gate-relaxation WARN the user did not accept; note it survives `sage install --force`.

## advisory_scope
- role_boundary: overlays an EXISTING CORE roster asset only (new assets → /sage-asset);
  writes the hand-authored overlay directly, NOT via generate; does not silently proceed
  past a gate-relaxation warning; the overlay must not relax AGENT_GUIDE, phase, review,
  or verification gates
- uses: retro/absorb overlay proposals (asset_id hint), docs/sage_harness/{agents,skills}/*.md,
  sage validate (overlay gate-relaxation lint)
- convention_doc: AGENT_GUIDE.md
- overlay: optional `sage/asset_overrides/skills/sage-asset-override.md` has project-local
  priority over CORE guidance and is not shipped by `sage install`; it must not relax AGENT_GUIDE, phase, review, or verification gates

## runtime_bindings
- claude: .claude/skills/sage-asset-override/SKILL.md (repo — Claude Code auto-discovers)
- codex:  $CODEX_HOME/skills/sage-asset-override/SKILL.md (global — codex does not auto-discover repo-scoped skills)

## drift_checks
- conformance: procedure step 5 (gate-relaxation check + explicit confirmation) and step 2 (CORE-roster-id only, new assets routed to /sage-asset) must be present
