---
domain_refs: [webrtc, security, recording, game]
---

## ChatForYou Project Rules

- Git commit and push are exclusively user-owned. Agents must not run either command.
- Never edit `chatforyou-desktop/src` directly. Change the web source and follow `docs/chatforyou_desktop.md` for synchronization.
- Every implementation and design change must state Backend, Frontend, and Desktop impact, including explicit N/A reasons.
- Read `.local/local_agent_guide.md` for the Obsidian routing and mandatory post-change knowledge capture contract.
- If the vault path is unavailable or a knowledge write-back fails, preserve a complete
  wiki-ready draft under `.sage/pending-wiki/` and follow
  `docs/chatforyou-agent/knowledge-capture-fallback.md`. Report the result as
  `DEGRADED/PENDING`; never claim vault capture completed.
- Keep `scripts/verify-changes.sh` project-local and use `docs/chatforyou-agent/verification.md` for its behavior.
- Project-specific PDCA and output extensions live under `docs/chatforyou-agent/`; CORE documents remain generic.
- Use `chatforyou_v2` as the PR base when discussing or preparing a PR.
