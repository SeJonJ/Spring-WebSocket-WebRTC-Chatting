---
id: chatforyou-lead
kind: agent
# AUTO-DRAFT (reverse_extract) — 사람이 intent/advisory_scope 검토·수정
---
## intent
chatforyou-dev-team의 팀 리더

## advisory_scope
- owns: chatforyou-desktop/src, springboot-backend/src/main, springboot-backend/src/test
- uses: gstack:office-hours, gstack:plan-eng-review, mcp:codegraph, skill_or_agent:chatforyou-qa-expert
- convention_doc: docs/nodejs_frontend.md, docs/springboot_backend.md
- role_boundary: (미검출)

## runtime_bindings
- claude/codex interpretive render (claims 는 {id}.claims.yml)
