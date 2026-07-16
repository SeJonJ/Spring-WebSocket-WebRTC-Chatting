---
id: backend-test-convention-checker
kind: agent
# AUTO-DRAFT (reverse_extract) — 사람이 intent/advisory_scope 검토·수정
---
## intent
Use this agent when test code needs to be validated — specifically to check recently changed test files (via git diff) against the backend-test-layer skill conventions, and update the PLAN file's checklist accordingly

## advisory_scope
- owns: springboot-backend/src/test/java
- uses: skill:backend-test-layer
- convention_doc: (미검출)
- role_boundary: (미검출)

## runtime_bindings
- claude/codex interpretive render (claims 는 {id}.claims.yml)
