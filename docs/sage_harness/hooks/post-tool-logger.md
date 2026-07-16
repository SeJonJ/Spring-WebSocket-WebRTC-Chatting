---
id: post-tool-logger
kind: hook
runtime_bindings:
  claude: { event: PostToolUse, matcher: "Write|Edit|MultiEdit", timeout: 5 }
  codex: { event: PostToolUse, matcher: "apply_patch", timeout: 5 }
---
## intent
Write/Edit(Claude) 또는 apply_patch(Codex) 완료 시 tracked 소스/plan 파일 변경을
세션 JSONL 로그에 기록한다. stop-compliance-report 가 이 로그를 집계한다.

## runtime_bindings
- claude: { event: PostToolUse, matcher: "Write|Edit|MultiEdit", input: tool_input.file_path(단일) }
- codex:  { event: PostToolUse, matcher: "apply_patch", input: command 본문 다중파일 파싱 }
- output: 없음(파일 append only). on_fail: 없음(항상 exit 0)

## canonical
scripts/sage_harness/hooks/post_tool_logger_core.py  →  decide(event, profile) -> decision
- core 도메인 기본값 0. profile(file_type_map) 외부주입 필수.

## adapter_contract
- contract_version: "1"
- 표준 event: { hook_id, hook_event_name, runtime, session_id, tool, branch, now_utc, changes:[{path(rel), op}] }
- 표준 decision: { kind, action(log|noop), log_file, log_entries:[{ts,tool,file,type,branch,session}], exit_code }
- profile(2번째 인자): { file_type_map:[{glob,type}](첫매치), skip_untyped, log_schema_version }
- adapter 책임: 입력추출(claude file_path 단일 → changes[1] / codex apply_patch → changes[N]) +
  branch·now_utc 관측 주입 + profile 로드($SAGE_PROFILE) + JSONL append IO + 경로바인딩(.claude↔.codex)

## reverse_extract 분류 (8범주 — profile_bound 신설)
- structural_io_adapter: 입력추출 (Claude 단일 file_path vs Codex apply_patch 다중파일 정규식)
- profile_bound (신설): file_type_map 경로글롭(백엔드 소스 경로 등) = 프로젝트 선언값 → profile (§7 I2). core엔 없음
- token_adapter: PROJECT_ROOT env명, 로그경로(.claude↔.codex)
- algorithm(공유, core): changes[] → profile 분류 → 로그엔트리. skip_untyped.
- noise(정규화): 주석, 따옴표, import 정렬

## unresolved (drift 표면화 — 사람 확인)
1. **plan-doc 글롭 drift**: Claude `*/plan_docs/*`(어디든) vs Codex `^plan_docs/`(루트만).
   컴포넌트 plan_docs({component}/plan_docs) 처리가 갈림. canonical = `*plan_docs/*`(둘 다 매칭)
   채택 — §7 I11(plan_docs + {comp}/plan_docs) 의도에 부합. **사람 확인 필요**.
2. **type=other 기록 drift**: Claude 는 미분류도 type=other 로 기록, Codex 는 skip.
   canonical = skip(skip_untyped:true) — "tracked type만 기록" 의도. Claude other 기록은 회귀로 봄. **사람 확인 필요**.

## tests
scripts/sage_harness/hooks/tests/test_post_tool_logger.py (7 PASS)
- core classification(6 type + plan-doc drift canonical) / skip_untyped / multi_changes
- adapter e2e(claude 단일·codex 다중) / skip parity / behavior parity
- now_utc·branch 고정으로 결정론
