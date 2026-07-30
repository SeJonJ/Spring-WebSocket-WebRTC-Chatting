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

UserPromptSubmit 처리 시작 시 `session-start-snapshot`의 write-once helper도 호출한다. 이는 SessionStart
누락·지연 시 첫 프롬프트를 06 baseline 보조 경로로 사용하기 위한 것이다. exclusive first-opportunity
claim으로 이미 존재하는 baseline을 덮지 않고, 첫 시도가 비활성·실패한 뒤 늦은 baseline도 만들지 않는다.
claim은 장기 중단 후 resume에도 첫 기회가 다시 열리지 않도록 자동 TTL 삭제하지 않는다.
claim 파일 자체를 만들지 못하면 늦은 baseline 차단을 보장할 수 없으므로 risk 포착보다 먼저 exit 2로
UserPromptSubmit을 차단한다. claim을 만든 뒤의 profile/baseline 게시 실패는 claim을 보존하고 Stop에서
degraded fail-closed로 판정한다.

## runtime_bindings
- claude: { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: plain text(stdout) }
- codex:  { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: hookSpecificOutput JSON }
- on_fail: capture/noop은 exit 0. 공유 baseline helper의 first-opportunity claim 생성 실패만 exit 2.

## canonical
scripts/sage_harness/hooks/capture_declared_risk_core.py  →  decide(event) -> decision
- 알고리즘(공유): 위험레벨 정규식 2패턴, 세션 sanitize, 2일 cleanup 선언, state {level, ts, excerpt}
- core 는 IO/시간호출 없음. now_utc 는 adapter 주입.

## adapter_contract
- contract_version: "1"
- 표준 event: { hook_id, hook_event_name, runtime, session_id, prompt, now_utc }
- 표준 decision: { kind, action(capture|noop), level, session_key, state_file, state, cleanup, exit_code, message_key }
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
- adapter end-to-end exit/state/output snapshot (claude·codex)
- now_utc 고정(SAGE_NOW_UTC)으로 timestamp 결정론
- test_hook_runtime.py/test_stop_compliance_report.py: SessionStart 부재 시 UserPromptSubmit baseline fallback
