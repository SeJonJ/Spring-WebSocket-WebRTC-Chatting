---
id: capture-declared-risk
kind: hook
runtime_bindings:
  claude: { event: UserPromptSubmit, matcher: "", timeout: 5 }
  codex: { event: UserPromptSubmit, matcher: "", timeout: 5 }
---
## intent
유저 프롬프트에서 명시적 risk level 선언(L0~L3)을 포착해 세션별로 저장한다.
pre-implementation-gate 가 읽어 effective level = max(감지, 선언)으로 게이트를 적용한다
(선언은 상향만 — 안전 바닥 유지).

포착은 좁게 한다 — 오탐 하나가 세션 전체를 그 레벨로 묶기 때문이다. 의문·가정 문장의 레벨 언급은
선언으로 보지 않고, 서로 다른 레벨을 함께 선언하면 비교·설명으로 보고 아무것도 포착하지 않는다.
접미사 없는 단순 언급(캐시 레벨·파일명·코드블록)은 선언 시도가 아니므로 모호함 판정에 세지 않는다.
모호해서 기각할 때는 그 사실을 사용자에게 알린다 — 조용히 넘기면 선언했다고 믿은 채 진행하게 된다.
잘못 포착됐을 때는 `위험도 선언 해제`(또는 `risk 선언 취소`)로 즉시 지운다. 해제도 같은 문장 필터를
거치므로 질문(`해제해야 하나요?`)이나 부정(`해제하지 마`)으로는 발동하지 않는다.

UserPromptSubmit 처리 시작 시 `session-start-snapshot`의 write-once helper도 호출한다. 이는 SessionStart
누락·지연 시 첫 프롬프트를 06 baseline 보조 경로로 사용하기 위한 것이다. exclusive first-opportunity
claim으로 이미 존재하는 baseline을 덮지 않고, 첫 시도가 비활성·실패한 뒤 늦은 baseline도 만들지 않는다.
claim은 장기 중단 후 resume에도 첫 기회가 다시 열리지 않도록 자동 TTL 삭제하지 않는다.
claim 파일 자체를 만들지 못하면 늦은 baseline 차단을 보장할 수 없으므로 risk 포착보다 먼저 exit 2로
UserPromptSubmit을 차단한다. claim을 만든 뒤의 profile/baseline 게시 실패는 claim을 보존하고 Stop에서
degraded fail-closed로 판정한다.

## runtime_bindings
- claude: { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: plain text(stdout) }
  UserPromptSubmit 은 exit 0 평문 stdout 이 컨텍스트로 승격되는 이벤트라 봉투가 필요 없다(PreToolUse 와 다름)
- codex:  { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: hookSpecificOutput JSON }
- on_fail: capture/noop은 exit 0. 공유 baseline helper의 first-opportunity claim 생성 실패만 exit 2.

## canonical
scripts/sage_harness/hooks/capture_declared_risk_core.py  →  decide(event) -> decision
- 알고리즘(공유): 위험레벨 정규식 2패턴, 강한 의문·가정 표지 + 문장끝 종결 어미 기각,
  다중 선언 레벨 기각, 해제 패턴(직후 부정 배제), 세션 sanitize, 2일 cleanup 선언,
  state {level, ts, excerpt}
- 종결 어미(`나요`·`가요` 등)는 문장 **끝**에서만 본다. 무경계로 잡으면 `지나가요` 같은 평서형
  동사에 걸려 같은 문장의 정당한 선언을 버린다.
- 문장 분리는 소수점·버전 표기(`3.5`, `L3.java`)에서 쪼개지 않는다. 쪼개지면 가정 표지가 레벨과
  분리돼 오탐이 된다.
- 판정 순서: 해제 → 포착. 무엇이 잘못 잡혔는지 설명하며 해제하는 프롬프트가 다시 선언으로 잡히면
  탈출구가 닫힌다.
- core 는 IO/시간호출 없음. now_utc 는 adapter 주입.

## adapter_contract
- contract_version: "1"
- 표준 event: { hook_id, hook_event_name, runtime, session_id, prompt, now_utc }
- 표준 decision: { kind, action(capture|clear|noop), level, session_key, state_file, state, cleanup, exit_code, message_key }
- action=clear: adapter 가 state_file 을 삭제한다(부재 시 무시). core 는 파일을 만지지 않는다.
- message_key=risk_declaration_ambiguous: 모호 기각 안내. 상태 파일은 건드리지 않는다.
- adapter 책임 3종:
  1. 입력추출: 런타임 stdin JSON → 표준 event
  2. 출력렌더: claude=plain text / codex=hookSpecificOutput JSON (메시지 텍스트는 런타임 프로토콜 — adapter 소유)
  3. 경로·env 바인딩 + 파일IO: CLAUDE_PROJECT_DIR/.claude/logs vs CODEX_PROJECT_ROOT/.codex/logs
- 공유 선행 IO: 같은 session_id로 `_ensure_session_06_snapshot` 호출(SessionStart fallback, write-once).
  이 helper의 nonzero 결과를 그대로 반환해 claim I/O 실패 뒤 risk 포착을 계속하지 않는다.

## reverse_extract 분류 (7범주)
- token_adapter: PROJECT_ROOT env명, 로그경로(.claude↔.codex)
- output_adapter: plain text ↔ hookSpecificOutput JSON, 메시지 텍스트(이모지/구두점)
- algorithm(공유): 레벨 정규식·cleanup·state — core 로 승격
- noise(정규화): 주석, 따옴표 스타일, import 정렬
- algorithm_delta/policy_delta/unresolved: **없음** (이 hook 은 순수 token+output adapter — 드리프트 없음)

## tests
scripts/sage_harness/hooks/tests/test_capture_declared_risk.py
- core decision parity (fixture 3종)
- 포착 정밀도: 실측 오탐 프롬프트 미포착, 정상 선언 유지, 의문·가정·다중 레벨 기각
- 해제 경로: 양 런타임 state 삭제, 부재 시 무오류, 해제가 포착보다 우선
- 모호 기각 안내: 양 런타임 노출, 무관 프롬프트·가정 질문에는 미노출
- adapter end-to-end exit/state/output snapshot (claude·codex)
- now_utc 고정(SAGE_NOW_UTC)으로 timestamp 결정론
- test_hook_runtime.py/test_stop_compliance_report.py: SessionStart 부재 시 UserPromptSubmit baseline fallback
