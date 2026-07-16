---
id: sage-asset
kind: skill
# CORE skill (neutral). Project specifics come from profile, not this spec.
# CORE framework bootstrap asset: hand-shipped by `sage install`, NOT manifest-tracked.
# The manifest/claims/validate loop is reserved for project-authored skills
# (spec + claims + render hash) created via the generate/extract flow.
---
## intent
Add or modify a SAGE governance asset (hook / agent / skill) through conversation:
interview intent, author the spec/renders (both claude and codex for interpretive
assets), then hand off to `sage generate` to extract and register.

## when_to_use
- After bootstrap, to add a new hook/agent/skill or modify an existing one
- When extending the team roster or adding a project-specific verification skill
- When the user says "/sage-asset", "add an agent/skill/hook", "modify an asset",
  "자산 추가", "에이전트/스킬/훅 추가·수정"

## procedure
1. Read context: profile (confirm bootstrapped), AGENT_GUIDE, bootstrap-authoring §5,
   existing assets under docs/sage_harness/.
2. Identify operation (add | modify) and kind (hook | agent | skill) and id.
3. Interview for intent: id, intent sentence, advisory_scope (owns/role_boundary/
   convention_doc), runtime_bindings; for hook also the deterministic check logic.
4. Author the source:
   - hook: spec docs/sage_harness/hooks/<id>.md + scripts/sage_harness/hooks/<id>_core.py
   - agent/skill: BOTH renders — claude (.claude/agents/<id>.md | .claude/skills/<id>/SKILL.md)
     AND codex (.codex/agents/<id>.md | .codex/skills/<id>/SKILL.md), semantically equivalent.
5. Handoff: hook → `sage generate --kind hook --write --target <...>`;
   agent/skill → `sage generate --kind <kind> --id <id> --write`
   (skill that codex must discover: add `--deploy-codex`).
6. Verify: `sage validate --check --schema --kind all`; never bypass a FAIL.

## advisory_scope
- role_boundary: does not edit generated artifacts to change assets (edit spec/render
  then regenerate); does not bypass validate FAIL; does not author single-runtime
  interpretive assets (codex 함께 — both renders required)
- uses: sage generate / sage validate / sage doctor, bootstrap-authoring.md
- convention_doc: AGENT_GUIDE.md
- overlay: optional `sage/asset_overrides/skills/sage-asset.md` has project-local
  priority over CORE guidance and is not shipped by `sage install`; it must not relax AGENT_GUIDE, phase, review, or verification gates

## runtime_bindings
- claude: .claude/skills/sage-asset/SKILL.md (repo — Claude Code auto-discovers)
- codex:  $CODEX_HOME/skills/sage-asset/SKILL.md (global — codex does not auto-discover repo-scoped skills)

## drift_checks
- conformance: procedure step 4 (author BOTH renders) and step 5 (sage generate handoff) must be present
