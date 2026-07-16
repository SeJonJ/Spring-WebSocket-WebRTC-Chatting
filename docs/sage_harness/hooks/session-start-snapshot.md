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
파일시스템 상태 비교는 그 구멍을 닫는다. 게이트 아님 → 항상 exit 0, parse 실패 silent.

스냅샷은 **게이트 활성(mode advisory/enforce + usable retro_note)이고 session_id 가 있을 때만** 쓴다:
비활성 프로젝트에서 매 세션 06 전체를 해싱하는 낭비와, session_id 부재 시 공유 파일 오염을 피한다.
기록은 원자적(temp+os.replace)이라 도중 종료로 잘린 baseline 이 Stop 에서 감지를 무음 bypass 하지 않는다.
오래된 session-snapshot-*.json 은 TTL 로 정리(무한 누적 방지 — capture-declared-risk 와 동일).

## runtime_bindings
- claude: { event: SessionStart, matcher: "", input: session_id }
- codex:  { event: SessionStart, matcher: "", input: session_id }
- output: 없음(.{host}/logs/session-snapshot-{session_id}.json 원자쓰기 only). on_fail: 없음(항상 exit 0)

## canonical
scripts/sage_harness/hooks/session_start_snapshot_core.py → decide(event, snapshot) -> decision  (pure)
- event = { session_id, now_utc }. snapshot = { exists, sha256:{정규키: 해시} }(adapter 관측값).
- decision = { action: write|noop, record }. write-once: exists 면 noop(resume/재-SessionStart 가 baseline
  을 덮어 초기 변경을 잃지 않게). core 도메인값 0 — 06 glob·해시·경로·게이트활성 판정은 전부 adapter.
- IO 오케스트레이션(06 해시·게이트 활성 게이팅·원자쓰기·스냅샷 정리) = hook_runtime.run_session_start_snapshot.
- manifest 추적: 이 core 는 canonical_hash + adapter_contract_version(CONTRACT_VERSION) 로 per-hook 스탬프.
  공유 IO(hook_runtime.py)는 top-level hook_runtime_hash 로 별도 추적.

## adapter_contract
- contract_version: "1"
- 표준 입력: { session_id }
- adapter 책임: profile 로드($SAGE_PROFILE) + root 해석 + stdin raw 전달. 경로바인딩(.claude↔.codex)은 io.HOST_DIR.
- fail-open: profile/스냅샷 기록 실패는 세션을 막지 않는다(로그기반 감지로 폴백 — union 이라 회귀 아님). silent 금지.

## reverse_extract 분류
- 공유 core: write-once 결정(decide)
- 공유(hook_runtime IO): 06 glob 해시·게이트 활성 게이팅·원자쓰기·스냅샷 TTL 정리·session_id 파일명 정규화
- token_adapter: 로그경로(.claude↔.codex = io.HOST_DIR)
- profile_bound: 06 glob(profile.pdca.phases) + 게이트 활성(pdca.retro + knowledge_capture) — core 도메인값 0

## tests
- test_hook_runtime.py: core decide(write/noop/write-once) + _snapshot_changed_06 status(ok/absent/no_session/corrupt) + 내용변경·신규 감지
- test_stop_compliance_report.py: Bash 작성 06 스냅샷 감지 BLOCK / write-once 보존 / 로그기반 폴백(회귀 없음) / degraded 표면화(무음 아님) / baseline 정상 시 노이즈 없음
- test_retro.py + test_retro_audit.py: W4 --no-vault skip 기록·게이트 통과·우회(임의 run_id) 거부·기록실패 rc2
