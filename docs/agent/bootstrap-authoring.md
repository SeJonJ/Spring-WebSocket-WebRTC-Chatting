# Bootstrap Authoring Protocol (Conversational)

Use this when a project is first set up, or when a new component/asset must be
introduced. It defines **how an agent turns user intent into SAGE-conformant
assets through conversation** — the user supplies intent, the agent authors to
the spec, and a deterministic backend registers and verifies. The user does not
hand-write profile values or specs; the agent does, under the user's approval.
Some assets (agent/skill renders) still need an interpretive runtime render step
after scaffolding — this protocol marks where.

This document is runtime-neutral. Stack specifics (languages, frameworks,
high-risk domains, component names) come from the conversation and land in
`sage/project-profile.yaml` — never in this file.

---

## Principle

| Layer | Who | Determinism |
|:---|:---|:---|
| Intent | user (conversation) | — |
| Authoring (profile values, specs, plan docs) | agent, to the spec | interpretive |
| Registration (`sage generate`) + verification (`sage validate`) | deterministic | deterministic |
| Agent/skill render from scaffold | runtime AI | interpretive |

The agent renders; the backend checks. `sage validate` is the gate — it catches
schema and profile-semantic errors. Note the schema's strict unknown-key check
covers the top-level keys and selected sections (`risk`, `pdca`,
`output_contract`); most other nested sections are validated as loose objects,
and `--schema` (manifest JSON Schema) needs the optional `jsonschema` package.
So validate is a strong guardrail, not a total type-checker — author carefully.

The user stays **in the loop**: the agent authors per the rules and the user
approves. This is not a turnkey generator — intent's owner is the human.

---

## Stages

### 1. Install
`sage install --host {claude|codex} --dest <project>` places the harness, the
neutral docs (this file included), and an **empty** `sage/project-profile.yaml`
(schema keys fixed, values blank). Nothing is governed yet.

### 2. Interview → profile authoring
The agent interviews the user for intent, then fills `project-profile.yaml`
**values** (never adds/removes schema keys — determinism constraint).

This is a **progressive conversation, not a form**: the agent takes one topic per
turn — proposing concrete values inferred from a repo scan, showing the signal it
inferred from, and asking a single focused confirm/correct question — rather than
dumping the whole list for the user to fill. Conduct the conversation **in Korean**
(English support is planned, not yet active); only the conversation is localized —
the **machine** profile values (paths, globs, commands, ids, schema keys) stay
language-neutral, while human-facing message values (e.g. `desktop_block_hint`)
are written in Korean too, matching the conversation. The agent only asks open-endedly when
the repo gives nothing to infer (e.g. which domains are security-sensitive). This
keeps authoring on the agent; the user supplies intent and approves. Surface the
decisions that genuinely need user intent; author the rest from them:

- `project.name` / `project.prefix`
- `components[]` — component boundaries (id + path globs + model). Filling this
  enables `sage generate --kind roster` to scaffold `implementer-<id>` specs.
  `model` is a work-intensity tier (`opus`=heavy / `sonnet`=standard), not a runtime
  model name: claude-host maps it to the Claude subagent model, codex-host treats it
  as a nominal tier (Codex uses its own model). On a codex-host project, present it as
  a tier choice, not a Claude-model recommendation.
- `risk.*` — derived from the stack and the high-risk domains the user names
  (e.g. secrets, auth, payments → `l3_*`). Cover the tier globs
  (`l0_pass_globs` / `l1_path_globs` / `l2_path_globs` /
  `l3_filename_globs` + `l3_content_keywords`), the `plan_glob`, and the
  `desktop_block_glob` / `desktop_block_hint` for generated/sync outputs. For L3 to
  be reviewable rather than hard-blocked, also set `risk.l3_review_strategy` (e.g.
  `claude_grep_first` | `codex_feature_signal`) — the review protocol blocks L3
  until one is selected.
- `verification.commands` — the deterministic build/test/lint commands for the stack.
- `file_type_map` — `{ glob, type }` first-match classification used for logging.
- `options.cross_model` — when true, Phase 05 review is opposite-runtime **only
  when reachable**; `sage doctor` resolves reachability from peer CLI availability
  (`which codex` / `which claude`) and falls back to clean-context same-runtime
  when the peer CLI is unavailable. No third-party tool is needed — SAGE calls
  the peer runtime directly (`codex exec` / `claude -p`). It is **not** resolved
  from `runtime.external_reviewer` (which records the intended preference only).
- **Review loop (Phase 05)** — the optional adversarial review-rework loop. Use the
  shared interview set below (§ Review loop + vault interview set). Both `sage-init`
  (first authoring) and `sage-profile-modify` (later editing) drive the *same* set.

Present the filled profile (or the consequential choices) for user approval.

#### Review loop + vault interview set (shared by sage-init and sage-profile-modify)

Single source of the loop questions so the two skills never drift. Every toggle gets
a one-line plain explanation (same style as the L0–L3 explanation). One topic per turn.

**Loop toggle** (default off — `pdca.review_loop.enabled`):
> "Phase 05 리뷰를 적대적 루프로 돌릴까요? (기본: 단발 리뷰)"
> · 단발(off) — reviewer 1회. 가볍고 빠름.
> · 루프(on) — 찾기→반박→수정을 수렴까지 반복(L2/L3만). 거짓양성 거르고 누락 줄이나 비쌈.

If **off**, leave `review_loop.enabled: false` and skip the rest. If **on**, author
`pdca.review_loop` (each value with its one-line meaning):

| ask | key | one-line meaning |
|---|---|---|
| 어떤 관점? (스택 기반 제안) | `lenses` | FIND 렌즈(엔진 어휘: correctness/security/concurrency/convention/lifecycle/performance/error_handling/data_integrity/api_contract). **렌즈 1개 = 라운드당 리뷰어 서브에이전트 1개** |
| L2·L3 최대 라운드? | `max_iterations` | 수렴 못 하면 이 횟수에서 BLOCKED (기본 L2:1·L3:3) |
| 토큰 예산? | `budget_tokens` | 누적 초과 시 BLOCKED (기본 L2:150k·L3:600k) |
| 반박자 수? | `refuters` | **라운드당** 반박자 수(전체 finding 을 한 번에 배치 판정 — finding 수와 무관). 생존=반증표 < 과반 (기본 2) |
| 연속 dry 라운드? | `dry_rounds` | K라운드 연속 신규 0 → 수렴 (기본 1) |
| 승인 불가 심각도? | `severity_block` | 미해결 시 APPROVED 차단 (기본 [P0,P1]) |
| cross-model 반박? | `cross_model` | `options.cross_model` 연동 — 이미 물었으면 그 값 재사용(새로 묻지 않음) |
| 06←05 audit 게이트 강도? | `report_gate_enforce` | 06 작성 시 05 가 가리키는 loop run 이 clean·closed·APPROVED·seq연속·degraded아님인지 검사. `advisory`(기본, WARN) / `enforce`(BLOCK — 모든 05 가 루프 돌 때만 안전) / `off`(마커만). 안정화 전 advisory 권장, 팀 합의 후 enforce |

> **비용(토큰) 감 잡기 — 이 값들이 곧 서브에이전트 수입니다.** 이 앞의 용어부터: **finding = 리뷰가 찾은 문제**, **refuter = 그 문제가 진짜인지 따지는 검사관**. Phase 05 루프는 서브에이전트로 돕니다:
> - **FIND**: `lenses` 개수만큼 리뷰어가 매 라운드 병렬로 뜹니다(렌즈 6개 = 라운드당 6개). 각자 코드를 읽습니다.
> - **REFUTE**: 검사관(`refuters`)이 매 라운드 그 수만큼 뜹니다 — **문제가 몇 개든 검사관은 라운드당 이 수로 고정**(전체 문제를 한 번에 배치 판정). 기본 2.
> - **cross_model**: **FIND 단계에** 반대 런타임(codex/claude) peer 리뷰어 1명을 더합니다(`sage cross-check`, 별도 토큰). 이건 문제를 *찾는* 쪽이라 검사관(refuters)과 역할이 다릅니다 — refuters 수를 늘리는 게 아닙니다.
> - 이게 **최대 `max_iterations` 라운드** 반복되고, 누적 토큰이 `budget_tokens` 를 넘으면 종료됩니다.
> 즉 **렌즈·refuters·라운드·cross_model 을 키울수록 토큰이 늘어납니다.** 안전-크리티컬이 아닌 앱은 렌즈를 3~4개로 줄이면 커버리지 대비 토큰을 크게 아낍니다.

**Vault outputs** — ask **only if the loop is on AND `knowledge_capture.vault_path` is set**
(one turn; otherwise skip entirely):
> "루프 산출물을 Obsidian vault 에도 남길까요? (vault_path 감지됨)"
> · 감사 대시보드 — 라운드별 발견/채택/수렴 추이를 vault 노트로 (plain 테이블, 플러그인 무관) → `knowledge_capture.loop_audit_dashboard`
> · 회고 노트 — `sage retro` 결과를 approved:false 노트로, vault 에서 검토·승인(human-gate) → `knowledge_capture.retro_note`
> · [둘 다 / 대시보드만 / 회고만 / 안 함]

These flags require `vault_path` (the master gate); `sage validate` WARNs if a flag is
true while `vault_path` is empty.

**PDCA knowledge scan/write-back** — ask when `knowledge_capture.vault_path` is set
(one turn, default both on):
> "개발 전후로 vault 지식 캡처를 자동 실행할까요?"
> · 사전 조회 — `/sage-plan`이 구현 전에 vault를 검색해 `.sage/knowledge_scan.md`를 갱신 → `knowledge_capture.scan_before_dev`
> · 개발 후 갱신 — `/sage-team` 완료 시 vault 노트와 `wiki/log.md`를 갱신 → `knowledge_capture.update_after_dev`
> · [둘 다 / 사전 조회만 / 개발 후 갱신만 / 안 함]

These are explicit host-side steps backed by `sage knowledge scan` and
`sage knowledge write-back`; they are not hidden background writes.

**Note convention — follow the vault's existing rules (do not impose).** When `vault_path` is set,
inspect the vault before proposing `knowledge_capture.note_convention`: list the target folder,
read 2–3 existing notes, and check for an index/log. Propose values from what you observe, then
confirm with the user (do not auto-detect at write time — record the decision in the profile):
> - `folder` / `filename_pattern` / `prefixes` — match the vault's existing layout & title prefix (e.g. `TECH - {title}.md`); if the vault uses no prefix, leave it empty.
> - `tags_style` — `frontmatter` / `inline` / `none`. Match how existing notes tag (YAML frontmatter vs a `태그:` line vs none). Default `frontmatter`.
> - `index` — the vault's index filename (e.g. `index.md`) if one exists and the user wants new notes linked there; **empty if the vault has no index** (write-back then skips index updates).
> - `required_structure` — per-PREFIX required body markers (line-start strings) the vault expects for each note
>   type. Inspect the vault's authoring rules (or ask the user) and record the markers each prefix must contain.
>   These markers should describe the vault's **deep-note skeleton** for meaningful (L2/L3) work — e.g.
>   `BUG: ["> [!abstract]", "## 배경", "## 설계 결정", "## 변경 내역", "## 검증", "## 재발 방지", "## 관련 문서"]`. On
>   write-back of a **new** note, `sage knowledge write-back` advisory-checks that these markers exist and WARNs
>   (never blocks) on omission. It verifies marker **existence only** (a deterministic skeleton check); content
>   depth is left to the skill prompt + the write-back skill's host depth self-review (advisory), not the CLI. PREFIX is matched exactly first, then
>   case-insensitively. **Leave `{}` (default) if the vault imposes no fixed structure — the check is then fully
>   off.** Confirm the markers with the user; do not invent a structure the vault does not actually require.

**Note depth scales with risk tier (skill-driven, not CLI-enforced).** The write-back skill authors L1
(trivial) notes as a few sentences and L2/L3 (meaningful) notes to the vault's full deep skeleton above,
matching the depth of the vault's own hand-written notes. In the 변경 내역 section, code is shown proportional
to change volume — small changes as the actual before/after snippet, large changes as pseudocode/walkthrough
anchored by `파일:함수:line`. `required_structure` (when configured) only checks that the L2/L3 skeleton markers
are present; the CLI never judges whether each section is deep enough (that stays with the skill prompt and the
skill's host depth self-review (advisory) — an independent human review only if the project sets one up separately).

This makes `sage knowledge write-back` honor the user's vault conventions deterministically instead of
imposing SAGE defaults (6th-test: frontmatter/index assumptions didn't match the vault).

### 3. Handoff to the deterministic backend
On approval, hand off — do not keep authoring registration artifacts by hand:

```
# hook registration + manifest stamp. Default --target claude.
sage generate --kind hook --write --target claude     # or: --target both (claude + codex)
# component implementer SCAFFOLDS (only if components[] is set):
sage generate --kind roster --write
# verification (default --kind hook; use --kind all to also check agent/skill):
sage validate --check --schema --kind all
```

Notes that matter:
- `sage generate --kind hook` writes registration for `--target` (default
  `claude`). For a cross-model project that runs both runtimes, use
  `--target both`; `hooks.register` in the profile is documentation, not a
  generate input.
- `sage generate --kind roster` only **scaffolds** `docs/sage_harness/agents/
  implementer-<id>.md`. Those specs still need a runtime AI render (both
  `.claude/agents/<id>.md` and `.codex/agents/<id>.md`), then
  `sage generate --kind agent --id <id> --write` reverse-extracts spec+claims and
  registers them in the manifest (render_hash for both runtimes) — roster alone
  does not complete them.
- `sage validate` defaults to `--kind hook`; pass `--kind all` to also validate
  agent/skill renders (only meaningful once they are registered).

A `validate` FAIL is the guardrail working — fix the value/spec the message
points to and re-run; never bypass.

### 4. Phase-first authoring (before any code)
The `pre-implementation-gate` blocks L2/L3 code edits until the phases required by
`profile.pdca.pre_implementation_required` exist. Author the plan docs first,
through the same conversation:

- `00-base_plan` — CONTEXT (why / what / impact / risk)
- `01-plan` — CONTENT (requirements / data schema / API contract)
- `02-design` — architecture / sequence / error codes
- For L2/L3 work scoped to one component, also author `{component}/plan_docs/`
  (code-level design) before root `03-implementation` — see `pdca-templates.md`
  "Writing order for L2/L3 changes".

Templates and the 00↔01 / 02↔03 boundaries are in `pdca-templates.md`. Only after
the required phases exist does the gate admit implementation; the cycle then
continues 03 → 04 → 05 (review, cross-model when enabled) → 06.

### 5. Asset additions later
The same loop applies to introducing a new hook/agent/skill after bootstrap, and
the **`/sage-asset` skill** drives it conversationally:
- **hook**: author the spec under `docs/sage_harness/hooks/<id>.md` + the canonical
  `scripts/sage_harness/hooks/<id>_core.py`, then `sage generate --kind hook --write`.
- **agent/skill** (interpretive): author BOTH runtime renders (`.claude/...` and
  `.codex/...` — codex 함께), then `sage generate --kind <agent|skill> --id <id>
  --write` reverse-extracts spec+claims and registers them (render_hash for both
  runtimes). It fails closed if either render is missing.
  - For a skill codex must discover, add `--deploy-codex` (copies the repo-canonical
    `.codex/skills/<id>/SKILL.md` to `$CODEX_HOME/skills/<prefix>-<id>/`; the manifest
    still tracks only the repo canonical). codex-host + non-empty `project.prefix` required.
Never edit a generated artifact directly (see AGENT_GUIDE safety boundaries).

---

## Signals of incorrect bootstrap
- Profile authored with a new top-level key → schema violation. Keys are fixed,
  fill values. (Nested unknown keys are strictly blocked only in `risk` / `pdca`
  / `output_contract`; other sections are looser — still do not invent keys.)
- Registration artifacts (`{host}/settings.json`, shims, agent renders) edited by
  hand → regenerate / re-render from spec instead.
- Cross-model project registered with `--target claude` only → codex side missing;
  use `--target both`.
- Code edited before the required phases exist for an L2/L3 change → the gate will
  block; author the phases first.
- `validate` FAIL bypassed to "move on" → the guardrail was right; fix the value.

## Related rules
- `AGENT_GUIDE.md` — Risk & Workflow Gate, safety boundaries
- `docs/agent/pdca-templates.md` — phase templates + separation + component-level order
- `docs/agent/review-protocol.md` — reviewer resolution (`sage doctor`), L3 review
- `docs/agent/risk-classification.md` — how `profile.risk` maps to levels
- `sage/project-profile.yaml` — the single mutable SSOT this protocol fills
