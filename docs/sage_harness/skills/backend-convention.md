---
id: backend-convention
kind: skill
# AUTO-DRAFT (reverse_extract) — 사람이 intent/when_to_use/procedure 검토·수정
---
## intent
백엔드 코드 컨벤션 검증 스킬

## when_to_use
- backend-codeconvention
- 백엔드 컨벤션 체크
- 백엔드 코드 리뷰
- 백엔드 코드 컨벤션 수행

## procedure
1. 변경 파일 감지
2. 백엔드 파일 필터링
3. 컨벤션 기준 로드
4. 검증 수행
5. 결과 리포트
6. 구현 가이드 업데이트

## advisory_scope
- uses: docs/springboot_backend.md, skill_or_agent:backend-convention-checker

## runtime_bindings
- claude .claude/skills/{id}.md / codex .codex/skills/{id}/SKILL.md
