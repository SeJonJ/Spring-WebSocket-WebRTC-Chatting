---
id: ""            # 예: pre-phase4-checklist-gate
kind: hook
---
## intent
이 hook이 무엇을 결정론적으로 차단/검사하는지 한 문장.

## runtime_bindings
- claude: { event: PreToolUse, matcher: "Write|Edit|MultiEdit" }
- codex:  { event: PreToolUse, matcher: "apply_patch" }
- on_fail: block            # block | warn | context — adapter가 exit code/JSON/stderr로 매핑

## canonical
# form=core_adapter: scripts/sage_harness/hooks/<id>_core.py (pure decide) + adapters/{claude,codex}/<id>.sh
# form=native:       scripts/sage_harness/hooks/<id>.sh (단일 정본, 예: write-guard)

## enforcement
- 차단 조건과 통과 조건을 명시 (enforcement는 hook 전용)

## tests
scripts/sage_harness/hooks/tests/test_<id>.py   # 결정론 회귀 (core/adapter)
