---
id: chatforyou-backend-expert
kind: agent
# AUTO-DRAFT (reverse_extract) — 사람이 intent/advisory_scope 검토·수정
---
## intent
chatforyou-dev-team의 백엔드 전문가

## advisory_scope
- owns: springboot-backend/src/main/java/webChat, springboot-backend/src/test/java/webChat
- uses: agent:backend-convention-checker, backend-development:backend-architect, backend-development:feature-development, backend-development:security-auditor, bkit:bkend-auth, bkit:bkend-cookbook
- convention_doc: docs/springboot_backend.md
- role_boundary: (미검출)

## runtime_bindings
- claude/codex interpretive render (claims 는 {id}.claims.yml)
