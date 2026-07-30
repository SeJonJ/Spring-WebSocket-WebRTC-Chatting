#!/bin/bash
# session-start-snapshot — Codex thin adapter (R1: 본문은 runtime/run_hook.py 단일소스)
# SSOT: scripts/sage_harness/hooks/runtime/hook_runtime.py::run_session_start_snapshot
# SessionStart 시 06 baseline(존재+해시) 스냅샷 기록 → Stop 훅 retro_gate 가 writer-독립 06 감지에 사용.
# profile 외부주입 필수($SAGE_PROFILE) — 없으면 통과. (generated artifact — 직접수정 금지)
PROJECT_ROOT="${CODEX_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CORE_DIR="${SAGE_HOOK_CORE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# 설치된 콘솔 엔트리포인트는 SAGE 패키지 인터프리터를 보장하므로 overlay L1도 활성이다.
# 단 수동/레거시 adapter가 SAGE_PROFILE을 명시했다면 그 입력을 보존하는 direct runtime 경로를 쓴다.
if [ -z "${SAGE_PROFILE:-}" ] && command -v sage-hook >/dev/null 2>&1; then
  exec sage-hook --runtime codex --hook session-start-snapshot --root "$PROJECT_ROOT" --core-dir "$CORE_DIR"
fi
# Python 해석(P3-11 이식성): SAGE_PYTHON override → python3 → python 폴백(Windows/Git Bash 대응)
PY="${SAGE_PYTHON:-python3}"; command -v "$PY" >/dev/null 2>&1 || PY=python
exec "$PY" "$CORE_DIR/runtime/run_hook.py" \
  --runtime codex --hook session-start-snapshot --root "$PROJECT_ROOT" --core-dir "$CORE_DIR"
