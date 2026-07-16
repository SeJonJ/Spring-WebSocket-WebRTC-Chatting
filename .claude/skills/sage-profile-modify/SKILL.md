---
name: sage-profile-modify
description: "Modify an existing sage/project-profile.yaml through conversation — change risk tiers, verification commands, the Phase-05 review loop, vault outputs, components, or options. Reads the current value, proposes a diff, WARNS about governance-gate consequences, then edits the profile and re-validates. Invoke when the user says /sage-profile-modify, change the profile, 루프 설정 바꿔, 리뷰 루프 수정, risk 글롭 수정, profile 수정, or wants to tune review_loop iterations/budget/lenses."
---

# sage-profile-modify — Conversational Profile Modification

This skill **modifies an already-bootstrapped** `sage/project-profile.yaml` through
conversation. It is the third conversational entry point:
- `/sage-init` — first authoring (0→1).
- **`/sage-profile-modify` — edit existing profile / governance values (this skill).**
- `/sage-asset` — add/modify governance assets (hook/agent/skill).
- `/sage-asset-override` — overlay an existing CORE agent/skill (project-local, --force-safe).

Authoritative protocol: `docs/agent/bootstrap-authoring.md`. Rules: `AGENT_GUIDE.md`.

Do not edit this CORE render directly (the write-guard blocks it and `sage install --force` overwrites it). For project-local customization use `/sage-asset-override`: SAGE materializes an eligible overlay into this render as a managed block and `sage validate` gates it. Overlays for gate-bearing assets without an independent oracle are not yet supported (validate reports them).

> This skill is a **CORE framework bootstrap asset** — hand-shipped by `sage install`,
> NOT manifest-tracked. Its reference spec lives at
> `docs/sage_harness/skills/sage-profile-modify.md`. Claude reads this render from the
> repo (`.claude/skills/sage-profile-modify/`); Codex reads it from the user-global
> skills dir (`$CODEX_HOME/skills/sage-profile-modify/`).

## What this skill is NOT

The profile is **hand-authored SSOT**, not a generated artifact — so this skill edits
the YAML **directly** and re-validates. It does **not** run `sage generate` (that is for
assets, where the write-guard forces spec→generate). `/sage-asset` is for changing
hooks/agents/skills; this skill is only for the profile's values.

## Hard rules

- **Fill/change values, never add or remove schema keys.** The schema is fixed; only
  values change. Adding a top-level key, or any key under a closed section
  (`risk` / `pdca` / `output_contract`), is a schema violation `sage validate` rejects.
- **Consequence-aware (this skill's core duty).** A profile change can *loosen or
  tighten the governance gate*. Before applying, state the effect in plain terms
  (see "Consequence warnings"). Editing the profile is editing the gate.
- **Never bypass a `sage validate` FAIL.** A FAIL is the guardrail working — fix the
  value it points to and re-run.
- **The user owns intent.** Propose the diff, surface the consequence, get explicit
  approval before writing.

## Step 0 — Read context first

Read, in order, before asking anything:
1. `sage/project-profile.yaml` — the file you will edit. If the profile is **not
   bootstrapped** — `project.name` empty, OR `risk` globs and `components` both unset
   (the same predicate `sage generate` enforces; a name-only profile is still toothless) —
   **stop and route to `/sage-init`**. This skill edits an established profile; it does
   not bootstrap.
2. `AGENT_GUIDE.md` — risk gate, PDCA phases, safety boundaries.
3. `docs/agent/bootstrap-authoring.md` — interview style + the shared "Review loop +
   vault interview set" (reuse it for review_loop/vault edits).

## Step 1 — Identify what to change (one focused turn)

From the user's stated intent, or by asking, pin the **section**:
- `project` (name/prefix) · `components[]` · `verification.commands` ·
  `risk.*` (L0–L3 globs / content keywords / `l3_review_strategy`) ·
  **`pdca.review_loop`** (the Phase-05 loop — use the shared interview set) ·
  `options.*` · **`knowledge_capture`** (vault_path + `loop_audit_dashboard` / `retro_note`) ·
  `file_type_map` · `compliance` / `output_contract` ·
  **`team.core.<role>.runtime`** (`model` / `effort`) · **`cross_model.effort`**.

**`team.core.<role>.runtime.{model,effort}`** are injected into `.claude/agents/<id>.md`
frontmatter, so editing the profile alone does nothing — finish with
`sage install --force` to re-render, then `sage doctor` to confirm no agent reports
`stale`. They bind on a claude host only. A bare `model:`/`effort:` directly on the role
(no `runtime:`) is a legacy dead field; move it under `runtime:`.

**`cross_model.effort`** only matters when `options.cross_model: true`. Unset → `high`.
The vocabulary is peer-specific (`codex`: `minimal|low|medium|high|xhigh`;
`claude`: `low|medium|high|xhigh|max`) and a wrong value is rejected by `sage validate`.

For **`pdca.review_loop`** and the **vault outputs**, drive the *same* questions as
`/sage-init` via `docs/agent/bootstrap-authoring.md` (§ Review loop + vault interview
set) — single source, so init and modify never diverge. (Vault turn applies only when
the loop is on AND `knowledge_capture.vault_path` is set.)

## Step 2 — Propose diff + consequence, get approval

1. **Show the current value** of the target key(s) verbatim.
2. **Propose the new value** as a before→after diff.
3. **State the consequence** in plain terms (this is mandatory, not optional):

### Consequence warnings (state before applying)

| change | consequence to surface |
|---|---|
| remove `risk.l3_filename_globs` / `l3_content_keywords` | that domain no longer gets the L3 gate/review (loosened) |
| empty/changed `risk.l3_review_strategy` | L3 becomes hard-blocked, or review matching changes |
| remove a phase from `pdca.pre_implementation_required` | that phase no longer required before code (gate loosened) |
| empty a `verification.commands` entry | that check (build/test/lint) is skipped |
| `review_loop.enabled` → false | Phase 05 reverts to single-pass review |
| lower `review_loop.max_iterations[L3]` | fewer rework rounds before BLOCKED (e.g. 1 ≈ single-pass) |
| lower `review_loop.budget_tokens` | the loop may BLOCK earlier on budget |
| narrow `review_loop.severity_block` | lower-severity findings no longer block APPROVED |
| empty `knowledge_capture.vault_path` | all vault features OFF |

4. Get **explicit approval** before writing.

## Step 3 — Apply the edit

Edit `sage/project-profile.yaml` **in place** — change only the approved value(s),
preserving the fixed schema keys. Do not reformat unrelated sections.

## Step 4 — Re-validate (always)

```
sage validate --schema --kind all
sage doctor
```
`validate` re-checks schema + semantics (typo / missing-tier / silent-disable);
`doctor` re-checks option dependencies (cross_model reachability, vault_path,
review_loop) and reviewer resolution. A FAIL points at the value to fix — **fix and
re-run, never bypass**. If you changed `components[]`, note that
`sage generate --kind roster` may be needed to scaffold new `implementer-<id>` specs
(that is an asset step — hand off or route to `/sage-asset`).

## Done

The change is complete when the profile reflects the user's intent, the consequence was
surfaced and accepted, and `sage validate` passes (or only WARNs the user accepted). If
the change tuned the review loop, the next Phase-05 run picks it up; if it touched a
gate-affecting section, the new gate behavior is live immediately.
