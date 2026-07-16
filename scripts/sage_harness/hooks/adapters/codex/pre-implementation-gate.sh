#!/bin/bash
# pre-implementation-gate — Codex thin adapter (R1: 본문은 runtime/run_hook.py 단일소스)
# SSOT: scripts/sage_harness/hooks/pre_implementation_gate_core.py (decide)
#       scripts/sage_harness/hooks/runtime/{hook_runtime,io_codex}.py (IO 오케스트레이션)
# 어댑터는 PROJECT_ROOT/CORE_DIR 해석 후 run_hook 을 exec 만 한다(임베드 Python 제거). (직접수정 금지)
PROJECT_ROOT="${CODEX_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CORE_DIR="${SAGE_HOOK_CORE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# Python 해석(P3-11 이식성): SAGE_PYTHON override → python3 → python 폴백(Windows/Git Bash 대응)
PY="${SAGE_PYTHON:-python3}"; command -v "$PY" >/dev/null 2>&1 || PY=python
exec "$PY" "$CORE_DIR/runtime/run_hook.py" \
  --runtime codex --hook pre-implementation-gate --root "$PROJECT_ROOT" --core-dir "$CORE_DIR"
