---
id: chatforyou-dev-team
kind: skill
# AUTO-DRAFT (reverse_extract) — 사람이 intent/when_to_use/procedure 검토·수정
---
## intent
ChatForYou v2 주요 기능 개발을 위한 5인 에이전트 팀 조율 워크플로우

## when_to_use
- (미검출)

## procedure
1. (docs 읽기 완료 후)  읽기
2. 컨벤션 기준으로 설계 타당성 검증
3. 기존 구현 가이드 존재 여부 확인 (, )
4. 분석 요약 작성 후 각 전문가에게 전달 (구현 가이드는 각 전문가가 직접
5. 파일 소유권 배분
6. 유저와 기능 범위·목적 논의 (소스 코드 수정 금지)
7. 유저 승인 후 분석 요약 작성 및 파일 소유권 배분
8. 병렬 개발
9. springboot-backend/src/main/ 개발
10. src/test/service/ 에 Service 단위 테스트 작성 (정
11. backend-convention-checker로 자체 검증
12. 잔존 항목이 있으면 구현 가이드 하단  또는 에 기록
13. 리더 분석 요약 수신
14. 구현 전 , ,  재확인
15. 작성 (기존 파일 있으면 병합)
16. nodejs-frontend/ 개발
17. frontend-convention-checker로 자체 검증
18. 검증 결과에 따라 구현 가이드 체크박스 갱신
19. 직접 수정 금지
20. QA
21. 백엔드 전문가 결과물 확인 (src/main/ + 단위 테스트)
22. 백엔드 전문가가 놓친 케이스 중심으로 시나리오 설계
23. @WebMvcTest (HTTP/인증/경계값) + @SpringBootT
24. backend-test-convention-checker로 검증
25. STEP 4 에서 lead 가 04-analyze 작성 시 QA Cove
26. 팀 리더 + QA(보조)
27. 02-design 과 03-implementation, 실제 구현 코드를
28. 가 STEP 3 에서 작성한 통합/경계/HTTP 테스트의 커버리지 검증 
29. 04 자체로 단독 판정(APPROVED/FAIL)을 내리지 않는다
30. 외부 전문가 + Codex 반복 검토 루프
31. Codex APPROVED → 루프 종료 → STEP 6
32. Codex FAIL → triage → 채택 항목 "Iteration 1
33. APPROVED → 루프 종료 → STEP 6
34. FAIL → triage → "Iteration 2 Required Fi
35. external-expert
36. 여전히 FAIL → Final Status
37. 팀 리더
38. 전원 결과물 취합
39. STEP 2 Exit Gate 충족 여부 확인 (구현 가이드 체크박스 +
40. 외부 전문가 Critical 항목 + Codex 교차검증 결과를 유저에게
41. Document Mapping 체크박스를 실제 파일 존재 여부 및 pha
42. 산출물 인벤토리를 06-report에 표로 남기고, STEP 6 완료를 
43. commit 메시지 추천 (실제 commit은 유저가 직접)
44. /Claude CLI 실패 시 자동 fallback을 순서대로 시도한다
45. 04 의  섹션에는 아래 항목을 반드시 포함한다
46. 1 iteration의 정의
47. 3-iteration stop rule
48. Claude 교차검증 (cross-model independent rev
49. Core WebRTC Architecture Gate
50. L2에서 외부 리뷰가 recommended인 경우에만, 사용자 명시 수용
51. L3에서 Claude CLI/별도 런타임 리뷰가 fallback까지 실패
52. L3에서 유저가 degraded fallback(별도 headless C
53. PLAN 파일 체크리스트 완료 표시
54. Risk별 review-rework loop 적용 기준
55. STEP 2 Exit Gate 충족 여부 확인
56. 결정론 검증 Gate
57. 결정론 검증 대상이 있는 경우  기준으로  실행 결과를 구현 가이드 또는
58. 데스크톱 반영이 필요하면  기준으로 수정 후 의 sync 절차로 처리
59. 백엔드/프론트/QA 전원 결과물 + STEP 4 의 04 gap find
60. 예외 처리/로그 표시 관련 미해결 항목이 있으면 구현 가이드 하단  또는
61. 외부 전문가 + Claude 교차검증
62. 외부 전문가 Critical 항목 + Claude 교차검증 결과를 유저에
63. 작업 산출물 인벤토리 표시 (MANDATORY)
64. 팀 의견 상충 지점, 누락 위험 요소 분석

## advisory_scope
- uses: bkit:audit, bkit:code-review, bkit:qa-phase, bkit:zero-script-qa, docs/chatforyou_desktop.md, docs/nodejs_frontend.md, docs/springboot_backend.md, gstack:browse

## runtime_bindings
- claude .claude/skills/{id}.md / codex .codex/skills/{id}/SKILL.md
