#!/bin/bash
# post-tool-logger — Claude thin adapter (R1: 본문은 runtime/run_hook.py 단일소스)
# SSOT: scripts/sage_harness/hooks/post_tool_logger_core.py (decide)
#       scripts/sage_harness/hooks/runtime/{hook_runtime,io_claude}.py (IO 오케스트레이션)
# profile 외부주입 필수($SAGE_PROFILE) — 없으면 noop. (generated artifact — 직접수정 금지)
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
CORE_DIR="${SAGE_HOOK_CORE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# Python 해석(P3-11 이식성): SAGE_PYTHON override → python3 → python 폴백(Windows/Git Bash 대응)
PY="${SAGE_PYTHON:-python3}"; command -v "$PY" >/dev/null 2>&1 || PY=python
exec "$PY" "$CORE_DIR/runtime/run_hook.py" \
  --runtime claude --hook post-tool-logger --root "$PROJECT_ROOT" --core-dir "$CORE_DIR"
