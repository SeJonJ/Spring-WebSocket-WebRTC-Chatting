---
id: pre-phase4-checklist-gate
kind: hook
runtime_bindings:
  claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", timeout: 10 }
  codex: { event: PreToolUse, matcher: "apply_patch", timeout: 10 }
---
## intent
04-analyze 문서 작성(Phase 3→4 전환 신호) 시, 해당 기능의 03-implementation + 컴포넌트 plan_docs
체크리스트에 미완료(- [ ])가 있으면 차단한다. EXIT 2=차단 / 0=통과(또는 03 미발견 경고).

## runtime_bindings
- claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", input: tool_input.file_path }
- codex:  { event: PreToolUse, matcher: "apply_patch", input: command Add/Update targets }
- output: block=메시지+exit2 (claude stdout / codex stderr), warn·ok=메시지+exit0 (codex hookSpecificOutput)

## canonical (IO-bound gate — 2단계 pure core)
scripts/sage_harness/hooks/pre_phase4_checklist_gate_core.py
- `plan_reads(event, profile) -> {base, globs, exact}`  : 읽을 후보 산출 (fs 접근 0)
- adapter 가 globs 로 fs_snapshot 생성 (glob_results + files, root-상대)
- `decide(event, profile, snapshot) -> decision`        : 게이트 판정 (fs/time 의존 0)
- core 는 완전 순수 — 모든 IO 는 adapter 가 snapshot 으로 주입 (replay/drift 비교 용이).

## adapter_contract
- contract_version: "1"
- 표준 event: { hook_id, hook_event_name, runtime, session_id, changes:[{path(rel), op}] }
- fs_snapshot: { glob_results: {glob: [path...]}, files: {path: text|null} }  (root-상대 경로)
- decision: { kind, status(block|warn|ok|skip), exit_code, base, total_unchecked, evidence[], message_key }
- adapter 책임: 입력추출(file_path / apply_patch) + fs_adapter(glob/read→snapshot) + 출력렌더 + 경로바인딩

## profile_bound (8범주 중)
- phase4_trigger_glob: "*plan_docs/04-analyze/*.md"
- checklist_scan_targets: [{label, glob, is_impl?}] — 03-implementation + 컴포넌트 plan_docs (§7 I11)
- suffixes: PDCA 산출물 네이밍 = framework 기본(DEFAULT_SUFFIXES) + profile override 가능

## reverse_extract 분류
- structural_io_adapter: file_path 단일 vs apply_patch Add/Update targets
- output_adapter: WARN/OK 렌더(claude plain vs codex hookSpecificOutput), block 채널
- token_adapter: PROJECT_ROOT env, 경로
- profile_bound: 트리거/타겟/suffixes
- algorithm(공유, core): base 추출(suffix 반복제거), find_match(exact우선+prefix양방향), 미완료 스캔, 판정
- **algorithm_delta 없음** (claude/codex 알고리즘 동일)
- read_error: evidence 추적만, block 판정엔 미반영(원본 동작 유지)

## tests
scripts/sage_harness/hooks/tests/test_pre_phase4_checklist_gate.py (9 PASS)
- core(in-memory snapshot): ok/warn/block(03·backend)/suffix/exact우선/read_error
- adapter(temp tree): claude·codex block·ok 동일 exit
