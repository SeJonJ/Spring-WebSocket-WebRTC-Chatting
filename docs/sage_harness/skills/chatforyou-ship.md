---
id: chatforyou-ship
kind: skill
# AUTO-DRAFT (reverse_extract) — 사람이 intent/when_to_use/procedure 검토·수정
---
## intent
기능/버그 개발 완료 후 chatforyou_v2 브랜치에 버전 태그와 함께 배포

## when_to_use
- (미검출)

## procedure
1. 현재 브랜치 및 버전 확인
2. 버전 일관성 검증
3. 배포 버전 결정
4. 버전 파일 업데이트 (bump 또는 불일치 수정 필요 시)
5. 메인 브랜치 머지 및 태그 push
6. GitHub Action 트리거 확인

## advisory_scope
- uses: (미검출)

## runtime_bindings
- claude .claude/skills/{id}.md / codex .codex/skills/{id}/SKILL.md
