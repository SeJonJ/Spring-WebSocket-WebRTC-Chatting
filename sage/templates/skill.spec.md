---
id: ""            # 예: backend-convention
kind: skill
---
## intent
이 스킬이 제공하는 워크플로우/지식 한 문장.

## when_to_use
- 트리거 상황 / 호출 시점

## procedure
1. 단계
2. 단계

## advisory_scope
- role_boundary: 이 스킬이 하지 않는 것
- uses: 참조 문서/도구

## runtime_bindings
- claude: .claude/skills/<id>/SKILL.md
- codex:  .codex/skills/<id>/SKILL.md

## drift_checks
- conformance: procedure/trigger presence lint (머신체크)
