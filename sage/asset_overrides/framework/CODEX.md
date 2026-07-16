---
domain_refs: []
---

## ChatForYou Codex Routing

- Launch the repository-local runtime with `CODEX_HOME=$PWD/.codex codex` or `./scripts/run-codex-local.sh`.
- Custom agents remain registered in `.codex/config.toml` and implemented by `.codex/agents/*.toml` plus their role markdown.
- Use project skills under `.codex/skills/` when their trigger matches.
- Report concrete plan, code, wiki, review, and skipped artifacts after coordinated development work.
