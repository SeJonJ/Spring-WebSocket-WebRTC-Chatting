---
id: pre-implementation-gate
kind: hook
runtime_bindings:
  claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", timeout: 10 }
  codex: { event: PreToolUse, matcher: "apply_patch", timeout: 10 }
---
## intent
소스/설정 변경 전 위험도(L0~L3)를 분류해 게이트를 적용한다. 동기화 산출물/금지 경로 직접수정 하드블록,
L3(profile.risk 고위험 도메인) + plan 없음 하드블록, L3 review 확인, L2 plan 확인.
PDCA phase 의무구조 강제(F9): profile.pdca 활성 시 구현 전 의무 phase 결핍이면 L2/L3 BLOCK·L1 WARN,
report phase 작성 전 approve phase APPROVED 확인. pdca 비활성이면 None → 기존 risk/plan 동작(하위호환).

## runtime_bindings
- claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", input: file_path + content/new_string/edits }
- codex:  { event: PreToolUse, matcher: "apply_patch", input: command 본문 다중파일+content }
- output: block=메시지+exit2 (claude stdout / codex stderr), warn·ok=exit0 (codex hookSpecificOutput)

## canonical (부분추출 — IO-bound gate, 2단계 pure core)
scripts/sage_harness/hooks/pre_implementation_gate_core.py
- `classify_risk(event, profile) -> {risk, reason, is_l3_filename, declared_l3, file_short}`
- `decide(event, profile, snapshot, strategy_result) -> {status, exit_code, risk, message_key, safety_degraded?}`
- core 는 fs/time 의존 0. plan 후보 내용은 snapshot, L3 review 매칭은 strategy_result(주입).

## algorithm_delta — 전략 슬롯 (사람 결정 완료 2026-06-13)
"L3 review doc 매칭"이 런타임마다 다른 알고리즘 → 둘 다 보존:
- scripts/sage_harness/hooks/strategies/pre_implementation_gate/claude_grep_first.py (grep-first)
- scripts/sage_harness/hooks/strategies/pre_implementation_gate/codex_feature_signal.py (토큰 스코어링)
- **find_l3_review(signals, snapshot) -> {found, path}** 공통 인터페이스.
- **canonical 결정: `codex_feature_signal`** (정교한 feature-signal 스코어링 채택, 사람 결정).
  profile.risk.l3_review_strategy 로 주입(독립 — 엔진 하드코딩 아님). adapter 가 CORE_DIR 의 전략 모듈 로드·실행.
  → L3 + plan 있음 + review 매칭 시 GATE OK, 매칭 실패 시 WARN. plan 없음은 여전히 hard block.
- 미선택(profile 에 strategy 없음) 시 = BLOCK + override-required + safety_degraded(안전 바닥, 다른 프로젝트 기본값).

## profile_bound (risk trigger = 프로젝트 선언값, §7 I2~I7)
profile.risk: { desktop_block_glob, l0_pass_globs, l3_filename_globs, l2_path_globs, l1_path_globs,
                l3_content_keywords, l2_content_keywords, plan_glob }
- canonical 매칭 = **case-insensitive**(G2, 더 많은 L3 포착 = 안전). 키워드/파일패턴 lower 비교.

## PDCA phase 강제 (F9, profile.pdca — 독립)
profile.pdca: { enabled, phases[{id,glob}], pre_implementation_required{L1,L2,L3}, report_phase, approve_phase, approve_marker }
- adapter 가 phase glob(root 상대, recursive) 스캔 → snapshot.phase_docs={id:[{path,content,recent}]}.
- core `decide`: ① report←approve 게이트(L0 단축 전, report dir 작성 시 approve 에 APPROVED 없으면 block_report_without_approval)
  ② 구현 전 의무 phase(`_missing_pre_impl_phases`, _doc_match=ticket→recent) — L2/L3 결핍=block_phase_incomplete, L1=warn_phase_incomplete.
- enabled=false/phases 없음 → `_pdca_cfg`=None → 강제 skip(기존 동작 보존). report dir 감지는 glob base-dir prefix(fnmatch `**` 불일치 회피).

## report←approve audit 게이트 (9.5, profile.pdca.review_loop.report_gate_enforce — F-5)
review_loop.enabled + report_gate_enforce ∈ {advisory, enforce} 일 때, 마커 검사에 더해 06 작성 시
`_audit_gate` 가: cycle 05 문서 1개를 `_doc_match`(ticket→recent)로 선택 → 그 동일 문서에서 APPROVED 마커
+ `Loop-Run: <run_id>` 를 함께 읽고, 주입된 `snapshot.loop_audit.runs[run_id]` 가 다음을 모두 만족하는지 검사:
clean(open 1회 + close 최대 1회 — 고아 close·중복/재사용 open·close 아님; open-only run 은 clean=True 이며 별도
`closed` 체크가 거른다) · seq_ok≠False(라운드 seq 연속 — 7차 배치3) · closed · result=APPROVED ·
degraded 아님(reviewer 의도=실제 — 7차 배치3). 위반 시 advisory=warn_report_without_audit(exit0) /
enforce=block_report_without_audit(exit2). report_gate_enforce 기본=advisory(키 부재 시 — 7차 배치3-5,
루프 켠 프로젝트는 최소 WARN); 명시 off·루프 비활성 → skip(하위호환). loop_audit 주입은 adapter
(`hook_runtime.build_snapshot` → `loop_audit.audit_summary`)가 담당(core 는 순수). stale 결합 차단: 마커와
Loop-Run 을 *같은* selected 문서에서 읽는다.
- **seq sanity(배치3-3)**: `loop_audit` 라이브러리가 open=0·round/close append 순 +1 로 seq 를 stamp →
  `audit_summary.seq_ok` 가 [0..n-1] 연속을 검산. **seq 를 생략했거나 순서를 틀린** 순진한/우회 수기 append 는
  seq 불연속(False)으로 탐지·차단되지만, **파일을 읽어 다음 정수를 추측해 맞춰 쓰면 통과한다**.
  **범위(codex R1b P1·R2 P2)**: 위변조 방지가 아닌 *게으른 우회/순서* 탐지 — 진짜 tamper-resistance 는
  해시체인(7차 이후 과제).
  구버전 기록(seq 전무)은 None=skip(하위호환). **레거시+신규 혼합**(같은 run_id 에 seq 없는 구레코드 +
  seq 있는 신규)은 의도적으로 False — 그 run 이력은 더 이상 신뢰 불가하므로 차단/경고(codex R1b P2, intentional).
- **reviewer degraded(배치3-4)**: open 의 reviewer_requested 가 명시됐는데 close 의 reviewer_actual 이
  *다르거나 기록 안 됨*(closed run 한정)이면 degraded → cross-model 요청이 same-runtime 으로 폴백/미확인된
  정황을 침묵 통과시키지 않음(codex R1b P1: actual 미기록도 fail-closed). reviewer_actual 자동 기록은 배치2
  (cross-model invocation)가 배선 — 그 전까지 req 미설정이면 degraded=False(오탐 없음).
- **report_gate_enforce 기본 advisory(배치3-5, 의도적 변경)**: 키 부재 시 off→advisory 는 *비차단 WARN*
  (exit0)이므로 hard break 아님 — 루프 켠 기존 프로젝트에 새 경고가 뜨는 것은 의도된 advisory-first 거동
  (codex R1b P2: 명시 off 는 여전히 skip, 마이그레이션은 advisory 관찰 후 enforce 전환).

## acceptance evidence 게이트 (verification.acceptance.report_gate_enforce)
build/test/lint 통과가 "사용자 요구사항 충족"을 자동 증명하지 않는 갭을 advisory-first 로 닫는다.
verification.acceptance.enabled + report_gate_enforce ∈ {advisory, enforce} 일 때, 06 작성 시
`_acceptance_gate` 가: cycle risk(declared→주입→00~05 문서 추정)가 require_for_risk(기본 L2/L3)에 들면
→ 01 문서의 acceptance matrix required ID 와 04 문서의 acceptance evidence table 을 `_doc_match`(ticket→recent)
로 선택해 대조. 04 문서 미선택 · 01 matrix required ID 없음 · evidence table 부재 · required ID 누락
· 미해결 상태(unresolved_statuses 기본 FAIL·NOT TESTED) · 미인식 상태값이면 위반. 위반 시
advisory=warn_report_without_acceptance(exit0) / enforce=block_report_without_acceptance(exit2).
acceptance 비활성 · off · cycle risk 가 *known* 이고 require_for_risk 밖이면 skip(하위호환); cycle risk
`unknown`(문서가 risk 라벨 미기재)은 skip 하지 않고 보수적으로 적용한다.
core 는 판단하지 않고 04 의 구조화된 상태(PASS/FAIL/NOT TESTED/N/A)만 확인한다.

## reverse_extract 분류
- 공유 core: 위험분류(경로/내용/declared), Desktop 블록, plan 존재 게이트, L2/L3 판정 구조
- structural_io_adapter: file_path vs apply_patch 다중파일+content
- output_adapter: 채널/메시지
- profile_bound: risk trigger 전부
- **algorithm_delta**: L3 review 매칭 (전략 슬롯, 병합금지)
- minor drift: content keyword case (Claude 고정대소문자 vs Codex (?i)) → canonical case-insensitive
  · **의도적 drift(audit P2)**: case-insensitive 는 원본보다 더 많은 L3 포착(안전 방향). 단 일반 문서/테스트에
    섞인 L3 키워드 문자열도 L3 로 올릴 수 있음. L0 문서(plan_docs/docs/*.md) pass 가 선행이라 문서 오탐은 제한됨.

## tests
scripts/sage_harness/hooks/tests/test_pre_implementation_gate.py (59 PASS)
- classify(L0~L3/escalation/desktop/declared/case-insensitive) + decide(분기) + 전략 후보 2종(인라인플래그/무효패턴 포함)
  + PDCA 강제(의무 phase block/통과/L3 review 보존/report 게이트/비활성 하위호환) + adapter(L3 block·L1 pass)
  + audit 게이트 seq_ok/degraded 분기 + report_gate_enforce 기본 advisory(7차 배치3)
  + acceptance evidence 게이트(matrix↔evidence 대조/미해결 block·warn/risk 미해당 skip)
