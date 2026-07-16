---
name: sage-init
description: Use at the start of a SAGE project (right after `sage install`) to fill `sage/project-profile.yaml` through a conversation, then hand off to `sage generate`/`sage validate`. Invoke when the user says "/sage-init" (Claude) or "$sage-init" (Codex), "bootstrap SAGE", "set up the profile", "SAGE 부트스트랩", or when the profile's project.name is empty.
---

# sage-init — Conversational SAGE Bootstrap

Invoke as `/sage-init` (Claude) or `$sage-init` (Codex).

Do not edit this CORE render directly (the write-guard blocks it and `sage install --force` overwrites it). For project-local customization use `/sage-asset-override`: SAGE materializes an eligible overlay into this render as a managed block and `sage validate` gates it. Overlays for gate-bearing assets without an independent oracle are not yet supported (validate reports them).

This skill turns user intent into a SAGE-conformant `sage/project-profile.yaml`
**through conversation**, then hands off to the deterministic backend
(`sage generate` / `sage validate`). The user supplies intent and approves; you
author the profile values to the schema. This is the designed entry point — the
governance gate is inert until the profile is bootstrapped, and `sage generate`
is BLOCKED while the profile is unbootstrapped (`project.name` empty, or
`risk`/`components` unset).

Authoritative protocol: `docs/agent/bootstrap-authoring.md`. Rules: `AGENT_GUIDE.md`.
This skill is the active driver of that protocol.

> This skill is a **CORE framework bootstrap asset**: hand-shipped by `sage install`,
> NOT a spec-generated skill (no `docs/sage_harness/skills/` spec, not manifest-tracked).
> Deploy location is runtime-specific: Claude reads it from the repo
> (`.claude/skills/sage-init/`, write-guard exempt); Codex auto-discovers it from the
> user-global skills dir (`$CODEX_HOME/skills/sage-init/`, default `~/.codex/skills/`)
> because Codex does not auto-discover repo-scoped skills. To change it, edit the
> framework template, not a spec.

## Hard rules

- **Fill values, never add/remove schema keys.** The schema is fixed; only values
  change (determinism constraint). Adding a top-level key, or any key under
  `risk` / `pdca` / `output_contract`, is a schema violation that `sage validate`
  rejects.
- **Never edit generated artifacts** (`.claude/settings.json`, hook shims, agent
  renders). Edit the spec and run `sage generate`.
- **Never bypass a `sage validate` FAIL.** A FAIL is the guardrail working — fix
  the value it points to and re-run.
- **The user owns intent.** Author per the rules, present the consequential
  choices, and get approval before handoff. This is not a turnkey generator.

## Step 0 — Read context first

Read, in order, before asking anything:
1. `sage/project-profile.yaml` — the file you will fill (confirm `project.name` is empty)
2. `AGENT_GUIDE.md` — risk gate, PDCA phases, safety boundaries
3. `docs/agent/bootstrap-authoring.md` — the full protocol and signals of incorrect bootstrap
4. The repo itself — list top-level dirs, detect stack/build files (package.json,
   build.gradle, pyproject.toml, etc.) so you can propose values instead of asking blind.

If `project.name` is already non-empty, the project is bootstrapped — stop and ask
whether the user wants to add a component/asset (Step 5) instead of re-running setup.

## Step 1 — Interview (progressive conversation, one topic at a time)

**This is a conversation, not a form.** Do NOT dump every question at once and ask
the user to answer a numbered list — that pushes the authoring work back onto the
user, which is exactly what this skill exists to avoid. Instead, walk one topic at
a time and drive each turn yourself.

### Language (mandatory)

Conduct the entire interview **in Korean** — every proposal, question,
acknowledgement, and progress summary. (English support is planned but not yet
active; default to Korean.) Only the **conversation** is Korean: the **machine** values you
write into `project-profile.yaml` stay language-neutral as-is — paths, globs,
command strings, component ids, strategy enums, and the fixed schema keys are
never translated. The one exception is **human-facing message values** such as
`desktop_block_hint` (a notice shown to the developer): write those in Korean too,
matching the conversation — they are prose, not machine tokens.

### Interview style (mandatory)

For **each** topic below, in order, take a single conversational turn:

1. **Propose, don't ask blind.** From your Step 0 repo scan, infer concrete values
   and state them as a proposal (e.g. "I see `build.gradle` and `src/main/java` —
   I'll set `verification.commands.build` to `./gradlew build`. Sound right?").
2. **Show the signal.** Name the file/evidence you inferred from in one short
   clause, so the user can judge the inference.
3. **Ask one focused question about *this topic only*.** The test is the user's
   *burden*, not the field count: a turn may present several **inferred** values at
   once for a single confirm (e.g. "here are the three risk globs I derived —
   correct?"), because the user only has to confirm. But never ask the user to
   *produce* more than one unknown per turn — when a value can't be inferred and
   the user must supply it (e.g. which domains are security-sensitive), that is its
   own turn with one open question. Batched *proposals* are fine; batched *demands*
   are the form-dump this skill forbids.
4. **Acknowledge and record**, then move to the next topic. Do not advance while
   the current topic is unsettled, and do not look ahead to later topics in the
   same turn.

Only when the repo scan gives you nothing to infer (e.g. which domains are
security-sensitive) do you ask open-endedly — and even then, one topic per turn.
Every 2–3 topics, briefly echo the profile-so-far so the user sees it taking shape.
Be thorough across the full topic list — a sparse profile means a weak gate — but
reach thoroughness through the back-and-forth, not a wall of questions.

### Topic order (one turn each)

1. **`project.name` / `project.prefix`** — propose from the dir name / package
   metadata. Name is the bootstrap signal; settle it first.
2. **`components[]`** — propose the partition from top-level dirs (e.g. backend /
   frontend) as `{ id, paths: [globs], model }`. Filling this enables
   `sage generate --kind roster` to scaffold `implementer-<id>` specs.
   - **`model` is a work-intensity tier, not a runtime model name.** `opus` = heavy
     (design-heavy / high-complexity components), `sonnet` = standard. On a **claude-host**
     project this tier maps to the Claude subagent model; on a **codex-host** project it is
     just a nominal intensity hint (Codex uses its own model regardless). So when the host
     is Codex, do **not** frame this as "recommending a Claude model" — say "heavier tier
     (`opus`)" or "standard tier (`sonnet`)". Allowed values stay `opus | sonnet`.
3. **`verification.commands`** — propose the real `build` / `test` / `lint` (and
   `syntax` for L1) from the build files you found. Empty = that check is skipped,
   so confirm only commands that genuinely exist.
4. **`risk` tiers L0–L2** — propose from file types. **Briefly explain what the
   levels mean as you set them**, since the user is choosing how strict each kind
   of file is gated. The levels are a blast-radius ladder — the gate enforces more
   the higher you go:
   - **L0** `l0_pass_globs` — docs / plan files. Passes instantly, no checks.
   - **L1** `l1_path_globs` — low blast radius (e.g. UI/markup). Light checks only.
     Also set `plan_glob` here (e.g. `plan_docs/**/*.md`) — where plan docs live.
   - **L2** `l2_path_globs` — source / config. Requires build + test + lint to pass.
5. **`risk` L3 (high-risk domains)** — the top of the ladder, reserved for areas
   where a mistake is costly. **Explain that L3 is the strictest tier: the gate
   requires the plan phases to exist before you may edit, and the change also needs
   independent review later in the workflow before it's considered done.** Here you
   usually must *ask*, not infer: which areas are
   security-sensitive (auth, payment, crypto, secrets)? From the answer set
   `l3_filename_globs` + `l3_content_keywords`, and the `desktop_block_glob` /
   `desktop_block_hint` for generated/sync outputs that must never be hand-edited.
   - Mention the **escalation rule** so the user understands the tiers interact:
     an L1/L2 file whose content matches `l3_content_keywords` is treated as L3,
     and the effective level is `max(detected, what the user declared)` — i.e. the
     gate always picks the stricter of the two.
   - **`l3_review_strategy`** — REQUIRED for L3 to be reviewable rather than
     hard-blocked. Confirm `claude_grep_first` or `codex_feature_signal` (or a
     module name). The review protocol blocks L3 until this is set.
6. **`file_type_map`** — propose `{ glob, type }` first-match classification for
   logging from the stack you've established.
7. **`team.core.<role>.runtime.model` / `.effort`** — optional per-agent runtime settings
   for the CORE roles (`leader`, `implementer-a`, `implementer-b`, `qa`, `reviewer`,
   `convention-checker`). Ask once, as a single topic; leaving both unset is a fine answer.
   Note the nesting: these live under `runtime:`, *not* directly on the role — a bare
   `model:` on the role is a legacy dead field and `sage validate` warns about it.
   - `model`: `opus | sonnet | haiku | fable | inherit`, or a full model id (`claude-…`).
     **Unset → the host CLI's own model.** SAGE never picks a model for you.
   - `effort`: `low | medium | high | xhigh | max`, or a positive integer.
     **Unset → `high`**, which SAGE injects rather than deferring to the CLI default.
   - These bind on a **claude host only** — they are injected into
     `.claude/agents/<id>.md` frontmatter. On a codex host `.codex/agents/*.md` has no
     mechanism to read them, so SAGE does not inject them and `sage validate` reports any
     that are set as inert. Don't offer the topic on a codex-host project.
   - Do not quietly pin `reviewer` or `qa` to a cheaper model or a lower effort than the
     rest — that silently weakens Phase 05 review. If the user wants that, make the trade
     explicit.
   - Changing these later requires `sage install --force` to re-render the agent files;
     `sage doctor` reports the un-re-rendered files as `stale` until you do.

Keep `pdca.*` at the standard 00–06 unless the user runs a different phase set
(don't raise it as a question unless they bring it up).

## Step 2 — Options

Same one-topic-per-turn style as Step 1: raise each toggle on its own turn, propose
a default, and only dive into the matching section if the user enables it. Skip a
toggle's detail entirely when it stays off.

- **`options.cross_model`** — when true, Phase 05 review runs opposite-runtime
  **only when reachable**. `sage doctor` resolves reachability from peer CLI
  availability: claude-host checks `which codex`, codex-host checks `which claude`.
  No third-party tool is required — SAGE calls the peer runtime directly
  (`codex exec` / `claude -p`). If enabling, confirm that `hooks.register`
  should be `[claude, codex]`.
  - **If the user enables cross_model**, confirm the peer CLI is installed:
    - claude-host: `codex` must be on PATH (`which codex`)
    - codex-host: `claude` must be on PATH (`which claude`)
    If the peer CLI is unavailable, `sage doctor` falls back to
    `clean_context_same_runtime` (same model, fresh context). Run `sage doctor`
    to verify the resolved reviewer mode before starting a cycle. If the user
    prefers not to install the peer CLI, that's fine — leave cross_model on with
    the same-runtime fallback, and say so.
  - **Only when cross_model is on**, optionally offer `cross_model.effort` — the reasoning
    effort SAGE passes to the peer CLI for its review. **Unset → `high`.** The vocabulary
    differs per peer and a wrong value is **silently ignored by codex**, so `sage validate`
    and `sage cross-check` reject it:
    - peer `codex` (claude-host): `minimal | low | medium | high | xhigh`
    - peer `claude` (codex-host): `low | medium | high | xhigh | max`
    The peer's **model** is never configurable from SAGE — that stays the peer CLI's own setting.
- **`options.obsidian` / `knowledge_capture`** — if used, set
  `knowledge_capture.vault_path` (empty path = vault features fully OFF) and the
  note convention. If a vault path is set, explicitly confirm the PDCA boundary
  automation flags:
  - `knowledge_capture.scan_before_dev` — `/sage-plan` runs `sage knowledge scan`
    before leader planning and refreshes `.sage/knowledge_scan.md`.
  - `knowledge_capture.update_after_dev` — `/sage-team` runs `sage knowledge write-back`
    after 06 completion to create/update the vault note and `wiki/log.md`.
  Default to both on unless the user declines; these are explicit host-side steps,
  not hidden background writes.
- **Review loop (`pdca.review_loop`)** — the optional Phase 05 adversarial loop.
  Raise it as its own toggle (default off). Drive it with the **shared interview set**
  in `docs/agent/bootstrap-authoring.md` (§ Review loop + vault interview set) so this
  skill and `sage-profile-modify` never diverge: loop on/off → if on, author
  `lenses` / `max_iterations` / `budget_tokens` / `refuters` / `dry_rounds` /
  `severity_block` / `cross_model` (reuse the `options.cross_model` value already
  settled above — do not re-ask). Each value gets its one-line meaning, per that set.
  Also surface that set's **token-cost note** (each lens = one reviewer subagent per round;
  `refuters` = reviewers per round batched over findings; cross_model adds a peer) so the
  user sets `lenses`/`refuters` knowing the subagent/token impact.
  - **Vault outputs (conditional)**: only when the loop is **on AND
    `knowledge_capture.vault_path` is set**, ask the one vault turn from the shared set —
    `loop_audit_dashboard` (감사 대시보드) and/or `retro_note` (회고 human-gate 노트).
    Skip this turn entirely when the loop is off or no vault is configured.
- **`options.codegraph` / `codegraph`** — toggle and MCP name.

MCP servers themselves are governed as the `mcp` asset kind
(`docs/sage_harness/mcps/{id}.md`); options here are just the toggles.

## Step 3 — Present for approval

Show the filled profile (or the consequential choices) and get explicit approval.
Call out anything you inferred rather than were told, so the user can correct it.

## Step 4 — Handoff + asset generation (ask auto vs manual)

After approval, ask the user how to generate the registration artifacts:

**Auto** — you run the handoff now (`--target` = this project's host runtime; use
`--target both` for cross-model):
```
sage generate --kind hook --write --target <claude|codex|both>
sage generate --kind roster --write                   # only if components[] is set
sage validate --check --schema --kind all
```

**Manual** — you print the exact commands and let the user/agent run them.

Notes that matter (from bootstrap-authoring.md):
- `--kind hook` default `--target claude`; match it to the host (`--target codex`
  on a Codex project), and use `--target both` for cross-model projects.
- `--kind roster` only **scaffolds** `implementer-<id>` specs; they still need a
  runtime AI render + `extract_agent --register` before they are manifest-registered.
- `sage validate` defaults to `--kind hook`; pass `--kind all` to also check
  agent/skill renders.
- A `validate` FAIL points at the value/spec to fix — fix and re-run, never bypass.

## Step 5 — Asset additions later (same loop)

To add a hook/agent/skill after bootstrap: interview → author the spec under
`docs/sage_harness/{hooks,agents,skills}/{id}.md` → register. Hooks register
deterministically via `sage generate`; agent/skill specs need an interpretive
runtime render plus extraction/registration.

## Done

Bootstrap is complete when `project.name` is set, the profile reflects the user's
intent, and `sage validate` passes (or only WARNs the user has accepted). From
here the normal PDCA phase-first flow applies — author plan docs before any L2/L3
code, or the `pre-implementation-gate` will block.
