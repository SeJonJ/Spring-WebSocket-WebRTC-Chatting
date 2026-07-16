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

## runtime_bindings
- claude: { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: plain text(stdout) }
- codex:  { event: UserPromptSubmit, input: stdin JSON(prompt, session_id), output: hookSpecificOutput JSON }
- on_fail: 없음 (capture/noop 모두 exit 0)

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
