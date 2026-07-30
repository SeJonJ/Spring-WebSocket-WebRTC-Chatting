# CLAUDE.md

Thin Claude-specific execution override. All common rules, workflow, and the
output contract are governed solely by `AGENT_GUIDE.md`.

## Mandatory read (session start)

1. `AGENT_GUIDE.md` — single source of truth
2. `sage/project-profile.yaml` — project values
3. `sage/project-profile.local.yaml` — machine values, when present
4. Relevant plan doc + convention docs (per profile)

## Claude-specific

- Use the Claude runtime asset ecosystem (`.claude/agents`, `.claude/skills`,
  `.claude/hooks`) which are generated from `docs/sage_harness/` specs.
- Do not modify generated artifacts directly — edit the spec and run
  `sage generate`. (Exception: hand-shipped CORE bootstrap renders under
  `.claude/skills/{sage-init,sage-init-local,sage-cycle,sage-plan,sage-team,sage-review,sage-asset,sage-asset-override,sage-profile-modify,sage-feedback}` and `.claude/agents/`
  CORE roster are not generated and are write-guard exempt — edit directly.)
