# AGENTS.md

Codex-native session entrypoint for this SAGE project. Codex auto-reads this file
at session start; it is a thin router, not a rules duplicate.

## Read in order

1. `AGENT_GUIDE.md` — the single source of truth (rules, risk gate, PDCA, safety).
2. `CODEX.md` — Codex-specific execution wrapper notes.
3. `sage/project-profile.yaml` — project values.

## Bootstrap first (if not done)

If `sage/project-profile.yaml` is unbootstrapped — `project.name` empty, or
`risk`/`components` unset — run the **conversational bootstrap FIRST, before any
other work**. The fastest path is the **`$sage-init` skill** (installed globally to
`$CODEX_HOME/skills/sage-init/` by `sage install --host codex`); invoke it with
`$sage-init`. It interviews the user → fills the profile values → hands off to
`sage generate` / `sage validate`. Underlying protocol:
`docs/agent/bootstrap-authoring.md`.

`sage generate` is BLOCKED until the profile is bootstrapped (by design — an empty
profile would silently disable the governance gate). So bootstrap is the required
first step, not optional.

(If `$sage-init` is not listed in `/skills`, re-run `sage install --host codex` to
install it globally, or follow `docs/agent/bootstrap-authoring.md` manually. Claude
runtime users invoke the same flow via the repo-scoped `/sage-init` skill.)

<!-- >>> SAGE OVERLAY v1 START (edit sage/asset_overrides/, not here) -->
## Project-Local Additions (sage/asset_overrides/framework/AGENTS.md)
아래는 이 프로젝트 로컬 추가 지침이며 CORE 기본 지침에 **더한다**.
AGENT_GUIDE·phase·review·verification·안전 경계를 **완화할 수 없다**.
## ChatForYou Agent Discovery

- Codex must also read `CODEX.md` and use the project-local runtime configuration.
- Claude coding sessions should load the applicable gstack workflow.
- Existing ChatForYou custom agent registrations remain project-owned extensions to the SAGE CORE roster.
<!-- <<< SAGE OVERLAY v1 END -->
