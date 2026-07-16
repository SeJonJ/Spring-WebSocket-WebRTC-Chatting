---
id: backend-convention-checker
kind: agent
# AUTO-DRAFT (reverse_extract) — 사람이 intent/advisory_scope 검토·수정
---
## intent
Use this agent when a plan file's lint verification stage needs to be executed — specifically to check recently changed backend files (via git diff) against the springboot_backend

## advisory_scope
- owns: (미검출)
- uses: (미검출)
- convention_doc: docs/springboot_backend.md
- role_boundary: (미검출)

## runtime_bindings
- claude/codex interpretive render (claims 는 {id}.claims.yml)
