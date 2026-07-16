---
id: sage-profile-modify
kind: skill
# CORE skill (neutral). Project specifics come from profile, not this spec.
# CORE framework bootstrap asset: hand-shipped by `sage install`, NOT manifest-tracked.
# The manifest/claims/validate loop is reserved for project-authored skills
# (spec + claims + render hash) created via the generate/extract flow.
---
## intent
Modify an already-bootstrapped sage/project-profile.yaml through conversation: read the
current value, propose a diff, WARN about governance-gate consequences, edit the YAML
directly (profile is hand-authored SSOT, not a generated artifact — no `sage generate`),
then re-validate. The profile-editing counterpart to /sage-init (first authoring) and
/sage-asset (assets).

## when_to_use
- After bootstrap, to change profile values: risk tiers, verification commands, the
  Phase-05 review loop (review_loop), vault outputs, components, options
- When tuning review_loop iterations/budget/lenses, or toggling vault dashboard/retro note
- When the user says "/sage-profile-modify", "change the profile", "루프 설정 바꿔",
  "리뷰 루프 수정", "risk 글롭 수정", "profile 수정"

## procedure
1. Read context: profile (if not bootstrapped — project.name empty OR risk globs and
   components both unset, the same predicate sage generate enforces → route to /sage-init,
   do not bootstrap here), AGENT_GUIDE, bootstrap-authoring (incl. shared Review loop +
   vault interview set).
2. Identify the target section (project/components/verification/risk/pdca.review_loop/
   options/knowledge_capture/file_type_map/compliance).
3. For pdca.review_loop and vault outputs, drive the SAME shared interview set as
   /sage-init (bootstrap-authoring.md) — single source, no drift. Vault turn only when
   loop on AND knowledge_capture.vault_path set.
4. Propose before→after diff and **state the gate consequence** in plain terms
   (loosen/tighten); get explicit approval. (Consequence warnings are mandatory.)
5. Edit profile.yaml in place — change only approved values, never add/remove schema keys.
6. Re-validate: `sage validate --schema --kind all` + `sage doctor`; never bypass a FAIL.
   (components[] change may need `sage generate --kind roster` — an asset step.)

## advisory_scope
- role_boundary: edits the profile (SSOT) directly, NOT via generate (that is for assets);
  does not add/remove schema keys; does not bypass a validate FAIL; does not bootstrap
  (routes to /sage-init when unbootstrapped)
- uses: sage validate / sage doctor, bootstrap-authoring.md (shared interview set)
- convention_doc: AGENT_GUIDE.md
- overlay: optional `sage/asset_overrides/skills/sage-profile-modify.md` has project-local
  priority over CORE guidance and is not shipped by `sage install`; it must not relax AGENT_GUIDE, phase, review, or verification gates

## runtime_bindings
- claude: .claude/skills/sage-profile-modify/SKILL.md (repo — Claude Code auto-discovers)
- codex:  $CODEX_HOME/skills/sage-profile-modify/SKILL.md (global — codex does not auto-discover repo-scoped skills)

## drift_checks
- conformance: procedure step 4 (consequence warning + approval) and step 6 (sage validate re-run) must be present
