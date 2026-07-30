---
id: session-start-snapshot
kind: hook
runtime_bindings:
  claude: { event: SessionStart, matcher: "", timeout: 10 }
  codex: { event: SessionStart, matcher: "", timeout: 10 }
---
## intent
세션 시작(SessionStart) 시 이번 세션의 06 문서 baseline(존재 + 내용 sha256)을 스냅샷으로 기록한다.
Stop 훅의 retro_gate 가 이 baseline 대비 변경분으로 **작성 도구와 무관하게** 이번 세션 작성 06 을 감지한다
(W2/P0-b). post-tool-logger 는 Write/Edit(claude)·apply_patch(codex)만 로깅해 Bash 로 쓴 06 을 놓치는데,
파일시스템 상태 비교는 그 구멍을 닫는다. 입력 parse 실패는 silent exit 0이지만, 첫 기회를 소비할 claim 자체를
기록하지 못하면 이후 늦은 baseline이 과거 변경을 흡수할 수 있으므로 exit 2로 작업 시작을 차단한다.

SessionStart가 누락·지연되는 host lifecycle에서도 첫 UserPromptSubmit이 agent 작업보다 먼저 실행되므로,
`capture-declared-risk`가 같은 write-once baseline helper를 보조 경로로 호출한다. 정상 SessionStart가 이미
기록했으면 noop하고, 보조 경로가 기록한 뒤의 UserPromptSubmit도 baseline을 덮지 않는다.

SessionStart와 UserPromptSubmit 경합은 `O_EXCL` first-opportunity claim으로 단일 승자만 허용한다. 첫 기회에
profile 오류나 게이트 비활성이면 claim만 남기고 baseline은 만들지 않는다. 이후 설정이 활성화돼도 이미 agent
작업이 시작된 뒤 늦은 baseline으로 과거 06 변경을 흡수하지 않으며, Stop은 baseline 부재를 fail-closed 처리한다.
claim은 승자·패자만 가를 뿐 완료를 보장하지 않는다 — 패자는 claim 파일의 `resolved`(noop|written) 마커로
승자의 시도가 끝났는지 확인하고, 미확정이면(승자가 claim 직후 중단됐을 수 있어 agent 작업이 baseline 게시보다
먼저 시작될 위험) exit 2로 진행을 막는다. 마커·baseline 레코드 모두 `session_id`로 재검증해, 파일명 정규화
충돌(sanitize+truncate)로 남의 claim·baseline을 내 것으로 신뢰하지 않는다. `resolved`의 다른 truthy 값은
손상된 claim으로 보고 미확정과 동일하게 차단한다. 이미 존재하거나 publish 경합에서 먼저 생긴 baseline도 정규
파일·동일 `session_id`·mapping `sha256`을 모두 검증한 뒤에만 agent 진행과 `written` 완료를 허용한다.

스냅샷은 **게이트 활성(mode advisory/enforce + usable retro_note)이고 session_id 가 있을 때만** 쓴다.
비활성 프로젝트는 작은 attempt claim만 쓰고 06 전체 해싱은 생략하며, session_id 부재 시 공유 파일 오염을 피한다.
기록은 완결된 temp 정규 파일을 hard link로 destination에 create-once 게시해 기존 baseline·symlink를 교체하지
않는다. hard link 미지원 파일시스템에서는 destination을 `O_EXCL`로 직접 생성하며, 완성 전 읽기는 corrupt로
fail-closed되어 기존 파일을 덮거나 false-pass하지 않는다.
Stop 읽기측도 no-follow 정규 파일만 신뢰한다. attempt claim과 이에 결속된 baseline은 장기 중단 후 resume을
보존하기 위해 자동 TTL 삭제하지 않고, claim 없는 legacy baseline·중단된 temp만 TTL로 정리한다.

## runtime_bindings
- claude: { event: SessionStart, matcher: "", input: session_id }
- codex:  { event: SessionStart, matcher: "", input: session_id }
- output: 없음(.{host}/logs/session-snapshot-{session_id}.json create-once 쓰기 only).
- on_fail: 입력/profile/baseline 게시 실패는 exit 0 후 Stop의 degraded 판정으로 귀결. first-opportunity claim
  생성 실패만 exit 2(SessionStart와 UserPromptSubmit 모두 작업 시작 차단).

## canonical
scripts/sage_harness/hooks/session_start_snapshot_core.py → decide(event, snapshot) -> decision  (pure)
- event = { session_id, now_utc }. snapshot = { exists, sha256:{정규키: 해시} }(adapter 관측값).
- decision = { action: write|noop, record }. write-once: exists 면 noop(resume/재-SessionStart 가 baseline
  을 덮어 초기 변경을 잃지 않게). runtime의 exclusive claim이 동시·늦은 writer도 차단한다.
  core 도메인값 0 — 06 glob·해시·경로·게이트활성 판정은 전부 adapter.
- IO 오케스트레이션(06 해시·게이트 활성 게이팅·원자쓰기·스냅샷 정리) =
  hook_runtime._ensure_session_06_snapshot. SessionStart와 UserPromptSubmit 보조 경로가 이를 공유한다.
- manifest 추적: 이 core 는 canonical_hash + adapter_contract_version(CONTRACT_VERSION) 로 per-hook 스탬프.
  공유 IO(hook_runtime.py)는 top-level hook_runtime_hash 로 별도 추적.

## adapter_contract
- contract_version: "1"
- 표준 입력: { session_id }
- adapter 책임: profile 로드($SAGE_PROFILE) + root 해석 + stdin raw 전달. 경로바인딩(.claude↔.codex)은 io.HOST_DIR.
- fail-open: profile/baseline 게시 실패는 즉시 세션을 막지 않고 Stop의 degraded 판정과 로그기반 감지로
  귀결한다. 단 first-opportunity claim 생성 실패는 늦은 baseline 방지를 증명할 수 없어 fail-closed exit 2.
  모든 실패는 silent 금지.

## reverse_extract 분류
- 공유 core: write-once 결정(decide)
- 공유(hook_runtime IO): SessionStart/UserPromptSubmit fallback·exclusive first-opportunity claim·claim
  resolved(noop|written) 마커·06 glob 해시·게이트 활성 게이팅·create-once 원자 게시·no-follow 정규 파일 읽기·
  claim 보존형 TTL 정리·session_id 파일명 정규화 + baseline/claim 내용 session_id 재검증
- token_adapter: 로그경로(.claude↔.codex = io.HOST_DIR)
- profile_bound: 06 glob(profile.pdca.phases) + 게이트 활성(pdca.retro + knowledge_capture) — core 도메인값 0

## tests
- test_hook_runtime.py: core decide(write/noop/write-once) + _snapshot_changed_06 status(ok/absent/no_session/corrupt) +
  내용변경·신규 감지 + UserPromptSubmit fallback/write-once + 동시 claim 단일 승자 + 늦은 baseline 차단 +
  snapshot symlink 거부 + create-once 게시 + hard link 미지원 `O_EXCL` 폴백 + claim I/O 실패 차단 +
  장기 재개 세션 claim/baseline 보존 + 미해결 claim 차단(codex 리뷰) + resolved=noop loser 진행 +
  resolved enum 강제 + claim/baseline session_id 불일치 차단 + publish 경합 baseline 재검증(codex 리뷰)
- test_stop_compliance_report.py: Bash 작성 06 스냅샷 감지 BLOCK / write-once 보존 / 로그기반 폴백(회귀 없음) / degraded 표면화(무음 아님) / baseline 정상 시 노이즈 없음
- test_retro.py + test_retro_audit.py: W4 --no-vault skip 기록·게이트 통과·우회(임의 run_id) 거부·기록실패 rc2
