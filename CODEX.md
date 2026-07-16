# CODEX.md

Thin Codex-specific execution override. All common rules, workflow, and the
output contract are governed solely by `AGENT_GUIDE.md`.

## Mandatory read (session start)

1. `AGENT_GUIDE.md` — single source of truth
2. `sage/project-profile.yaml` — project values
3. Relevant plan doc + convention docs (per profile)

## Codex-specific

- Use the Codex runtime asset ecosystem (`.codex/agents`, `.codex/skills`,
  `.codex/hooks`) which are generated from `docs/sage_harness/` specs.
- Do not modify generated artifacts directly — edit the spec and run
  `sage generate`. (The hand-shipped CORE bootstrap skills — `sage-init`,
  `sage-cycle`, `sage-plan`, `sage-team`, `sage-review`, `sage-asset`, `sage-profile-modify` — install to the user-global `$CODEX_HOME/skills/`,
  not the repo, so they are not generated artifacts; update them via reinstall.)
- The CORE roster agent renders (`leader`, `implementer-a`, `implementer-b`, `qa`,
  `reviewer`, `convention-checker`) are hand-shipped to repo `.codex/agents/<id>.md`
  (write-guard exempt, not generated). Codex has no native subagent invocation, so
  reference them as role definitions via this router; update them via reinstall.

<!-- >>> SAGE OVERLAY v1 START (edit sage/asset_overrides/, not here) -->
## Project-Local Additions (sage/asset_overrides/framework/CODEX.md)
아래는 이 프로젝트 로컬 추가 지침이며 CORE 기본 지침에 **더한다**.
AGENT_GUIDE·phase·review·verification·안전 경계를 **완화할 수 없다**.
## ChatForYou Codex Routing

- Launch the repository-local runtime with `CODEX_HOME=$PWD/.codex codex` or `./scripts/run-codex-local.sh`.
- Custom agents remain registered in `.codex/config.toml` and implemented by `.codex/agents/*.toml` plus their role markdown.
- Use project skills under `.codex/skills/` when their trigger matches.
- Report concrete plan, code, wiki, review, and skipped artifacts after coordinated development work.
<!-- <<< SAGE OVERLAY v1 END -->
