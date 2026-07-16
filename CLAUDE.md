# CLAUDE.md

Thin Claude-specific execution override. All common rules, workflow, and the
output contract are governed solely by `AGENT_GUIDE.md`.

## Mandatory read (session start)

1. `AGENT_GUIDE.md` — single source of truth
2. `sage/project-profile.yaml` — project values
3. Relevant plan doc + convention docs (per profile)

## Claude-specific

- Use the Claude runtime asset ecosystem (`.claude/agents`, `.claude/skills`,
  `.claude/hooks`) which are generated from `docs/sage_harness/` specs.
- Do not modify generated artifacts directly — edit the spec and run
  `sage generate`. (Exception: hand-shipped CORE bootstrap renders under
  `.claude/skills/{sage-init,sage-cycle,sage-plan,sage-team,sage-review,sage-asset,sage-profile-modify}` and `.claude/agents/`
  CORE roster are not generated and are write-guard exempt — edit directly.)

<!-- >>> SAGE OVERLAY v1 START (edit sage/asset_overrides/, not here) -->
## Project-Local Additions (sage/asset_overrides/framework/CLAUDE.md)
아래는 이 프로젝트 로컬 추가 지침이며 CORE 기본 지침에 **더한다**.
AGENT_GUIDE·phase·review·verification·안전 경계를 **완화할 수 없다**.
## ChatForYou Claude Routing

- Preserve project agents, commands, and skills under `.claude/`.
- Use gstack skills for Claude coding, review, QA, security, and shipping workflows when applicable.
- The ChatForYou shipping workflow remains the project-specific release entry point.
<!-- <<< SAGE OVERLAY v1 END -->
