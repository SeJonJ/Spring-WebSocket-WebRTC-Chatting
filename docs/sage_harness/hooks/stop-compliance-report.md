---
id: stop-compliance-report
kind: hook
runtime_bindings:
  claude: { event: Stop, matcher: "", timeout: 15 }
  codex: { event: Stop, matcher: "", timeout: 15 }
---
## intent
세션 종료(Stop) 시 session-{today}.jsonl 을 집계해 compliance 리포트(compliance-{today}.md)를 생성한다.
활동요약 + gate compliance(백엔드+plan / L3 패턴 / convention 안내) + 수정파일 목록 + policy_results.
리포트 생성은 항상 하되, retro_gate(9-C) enforce 가 미완료 사이클을 잡으면 양 host 모두 종료를 1회 막는다.
Claude는 exit 2, Codex는 stdout `{"decision":"block","reason":"..."}` + exit 0을 사용한다. Codex는 같은
turn을 다시 실행하고 다음 Stop 입력에 `stop_hook_active=true`를 보내며, 이 재시도에서는 WARN으로 완화해 통과한다.
enforce 미설정(기본 off)이면 종전대로 항상 통과한다.

## runtime_bindings
- claude: { event: Stop, input: .claude/logs/session-{today}.jsonl, output: 파일쓰기 + report path(plain) }
- codex:  { event: Stop, input: .codex/logs/session-{today}.jsonl, output: 파일쓰기 + 통과 시 무출력 / 차단 시 decision:block }
- block wire: Claude=exit 2. Codex=exit 0 + 단일 JSON `decision:block`(reason에 compliance 경로 포함).
  Codex Stop은 hookSpecificOutput.additionalContext를 허용하지 않아 단독·결합 모두 hook failure가 된다.

## canonical (부분추출 — 공유 집계만)
scripts/sage_harness/hooks/stop_compliance_report_core.py
- `decide(event, profile, snapshot) -> report_model`  (pure)
- `render_markdown(report_model) -> str`               (pure)
- snapshot = { entries[], today, branch, runtime } (adapter 가 JSONL 읽어 주입)
- report_model.sections = { header, activity_summary, gate_compliance{issues[]}, modified_files[], policy_results[] }
- 공유 gate 3종: backend_without_plan(WARN) / l3_pattern_detected(NOTICE) / backend_convention_reminder(INFO)

## ⚠️ policy_delta — 병합 금지 (정책 모듈 보존)
정책 모듈은 canonical core 에 자동병합 안 함 → policies/ 보존, policy_results 확장슬롯에만 주입:
- policies/output_contract_check.py: **Codex-only**(transcript 결합). manifest.unresolved "promote_output_contract_semantics?"
- policies/knowledge_capture.py: **OPTION(knowledge_capture, obsidian)**. vault_path 비면 N/A. CORE 아님.
- policies/retro_gate.py: **공유(양 host)**, 9-C Loop C 게이트. `pdca.retro.report_gate_enforce`(off|advisory|enforce)로
  `sage retro --check` 실행 여부를 세션 종료 시 사후 확인. enforce는 host별 차단 wire로 실제 종료를 막는다. retro_audit.jsonl(감사 트레일)에
  성공(retro_check_ok)·미완료(retro_check_missing)·노트생략(retro_check_skipped, --no-vault)을 append. **enforcement 라
  hook_runtime_hash 로 추적**(advisory 인 위 둘과 달리 부재 시 게이트가 조용히 무동작하므로).
  06 감지는 로그기반 ∪ 세션 baseline 스냅샷(writer-독립 — Bash 작성 06 포착, W2). baseline은
  SessionStart에서 기록하고 첫 UserPromptSubmit이 보조한다. 둘 다 미발화하거나 baseline이 손상돼
  writer-독립 감지가 불가하면(session_id 부재 포함) **enforce 는 fail-closed BLOCK**,
  advisory·재시도(stop_hook_active)는 WARN — 놓친 Bash-06 가능성을 조용히 통과시키지 않는다. snapshot은
  no-follow 정규 파일만 신뢰하므로 symlink·비정규 파일도 손상 상태로 분류한다.
- policies/writeback_depth_gate.py: **공유(양 host)**, L2/L3 write-back 심층 노트가 host depth self-review 를 거쳤는지
  `pdca.writeback.depth_review_gate`(off|advisory|enforce)로 세션 종료 시 사후 확인. 이번 세션 L2/L3 06(Risk Level 미기재=보수적 L2)이
  헤더 메타블록에 `Depth-Self-Review: performed` 를 자기선언했는지 검사 — 품질이 아니라 self-review 실행 증거만 본다(깊이 판정은
  skill·host 소관, false-assurance 회피). 미선언 시 enforce 첫 Stop=BLOCK / advisory·재시도=WARN. retro_gate 와 같은 06 감지
  (로그기반 ∪ SessionStart 스냅샷)·1회 block 제약을 공유하며, 둘 다 BLOCK 이면 한 번의 block 에 문구를 합쳐 싣는다. **enforcement 라
  hook_runtime_hash 로 추적**. update_after_dev(write-back) 가 꺼지면 강제할 노트가 없어 무동작(INFO).

## profile_bound
- L3 패턴 단일소스 = **profile.risk.l3_filename_globs 재사용**('*' strip + lower substring). pre-impl-gate 와 동일 소스(drift 방지),
  단 의미 다름(pre-impl=사전차단 / stop=사후감사). severity/behavior 는 비공유.

## reverse_extract 분류
- 공유 core: JSONL 집계, activity_summary, gate 3종, report_model, markdown 렌더
- token_adapter: 로그경로(.claude↔.codex)
- output_adapter: Claude plain text+exit 2 ↔ Codex decision:block JSON 또는 무출력 통과
- profile_bound: L3 패턴(공유 소스)
- **policy_delta**: output_contract(Codex-only) + knowledge_capture(OPTION) + retro_gate(공유, enforcement) — 보존만, 미병합

## tests
scripts/sage_harness/hooks/tests/test_stop_compliance_report.py + test_retro_gate.py + test_retro_audit.py
- core(gate 3종/집계/빈로그/render) + 정책모듈 보존 + adapter e2e(claude·codex)
- retro_gate(9-C): enforce 첫 Stop host별 차단 wire / stop_hook_active 재시도 통과 / advisory·off 미차단 / 세션스코프·표준 ** glob·
  Loop-Run 결속·멀티마커 skip / Codex decision:block·재시도 무출력 통과 / retro_audit ok·missing 이벤트 + 상태변화 dedup
