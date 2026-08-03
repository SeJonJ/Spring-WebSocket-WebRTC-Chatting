---
id: "chatforyou-dual-implementation-doc-gate"
kind: hook
runtime_bindings:
  claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit", timeout: 10 }
  codex: { event: PreToolUse, matcher: "apply_patch", timeout: 10 }
---
## intent

Phase 04 진입 전에 ChatForYou 컴포넌트(backend/frontend)별 구현 문서 계약을 결정론적으로 검사한다.
영향받는 컴포넌트는 같은 cycle-stem 의 구현 문서가 존재하고 완료돼야 하며, 영향이 없는 컴포넌트는
같은 stem 의 00 base-plan 에 비어 있지 않은 N/A 사유를 남겨야 한다.

## canonical
# form=core_adapter: scripts/sage_harness/hooks/chatforyou_dual_implementation_doc_gate_core.py (pure decide)

## enforcement

- 트리거: `plan_docs/04-analyze/<stem>.md` 변경. 그 외 경로는 skip.
- rollout 시점 스냅샷인 `LEGACY_CYCLE_STEMS` 의 stem 은 소급 검사하지 않는다(skip).
- 신규 stem 은 `plan_docs/00-base_plan/<stem>.md` 가 있어야 한다.
- 00 은 `ChatForYou-Component-Doc-Gate: v1` 과 `Component-Backend:` · `Component-Frontend:` 를
  각각 정확히 한 번 선언해야 한다. 선언은 fenced code block 밖에서만 인정한다.
- 상태는 `REQUIRED` 또는 `N/A: <사유>` 만 허용하며 N/A 사유가 비면 차단한다.
- `REQUIRED` 컴포넌트는 대응 구현 문서가 존재해야 하고, 미완료 체크박스(`- [ ]`)가 하나라도 있으면
  컴포넌트·파일·줄번호 증거와 함께 차단한다.
- root 03 문서 검사는 CORE `pre-phase4-checklist-gate` 가 계속 소유한다 — 여기서 중복하지 않는다.

## tests
scripts/sage_harness/hooks/tests/test_chatforyou_dual_implementation_doc_gate.py
