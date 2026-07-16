#!/usr/bin/env python3
"""run_hook — 설치된 thin 어댑터의 단일 진입점 (외부검토 R1 / P0-1).

shell 어댑터에 임베드돼 복제되던 Python 을 hook_runtime + io_{runtime} 로 들어올린 뒤,
어댑터 셸은 이 파일을 exec 만 한다(본문 단일소스). 입력: --runtime/--hook/--root/--core-dir, raw=stdin.

branch 는 SAGE_GATE_BRANCH 우선, 없으면 root 기준 git 으로 해석(원본 셸 BRANCH 로직 이식).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))   # .../scripts/sage_harness/hooks/runtime
sys.path.insert(0, HERE)
import hook_runtime as hr   # noqa: E402
import io_claude            # noqa: E402
import io_codex             # noqa: E402

_IO = {"claude": io_claude, "codex": io_codex}


def dispatch(runtime, hook, root, core_dir, raw_text):
    """hook id → hook_runtime 실행 (단일소스). 셸 어댑터(run_hook.main)와 `sage-hook`
    콘솔 엔트리포인트(sage.hook_entry)가 공유한다.

    policy 코어(core_adapter)는 hook_runtime 함수로, native 훅(순수 bash, 예: write-guard)은
    정본 `{core_dir}/{hook}.sh` 를 stdin JSON 으로 실행한다 — sage-hook 등록이 native 훅에 대해
    조용히 rc 0 로 통과하면(과거 갭) write-guard 가 프로덕션에서 무력화되기 때문. 정본 .sh 도 없는
    미지원 hook 만 안전 통과(rc 0)."""
    io = _IO[runtime]
    if hook == "pre-implementation-gate":
        return hr.run_pre_implementation_gate(io, root, core_dir, raw_text)
    if hook == "capture-declared-risk":
        return hr.run_capture_declared_risk(io, root, core_dir, raw_text)
    if hook == "post-tool-logger":
        return hr.run_post_tool_logger(io, root, core_dir, raw_text)
    if hook == "pre-phase4-checklist-gate":
        return hr.run_pre_phase4_checklist_gate(io, root, core_dir, raw_text)
    if hook == "stop-compliance-report":
        return hr.run_stop_compliance_report(io, root, core_dir, raw_text)
    if hook == "session-start-snapshot":
        return hr.run_session_start_snapshot(io, root, core_dir, raw_text)
    native = os.path.join(core_dir, f"{hook}.sh")
    if os.path.isfile(native):
        # 정본 .sh 는 stdin JSON(PreToolUse 어댑터 경로)을 읽고 exit 2 로 block 한다.
        return subprocess.run(["bash", native], input=raw_text or "", text=True).returncode
    return 0   # 미지원 hook id → 안전 통과


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", required=True, choices=["claude", "codex"])
    ap.add_argument("--hook", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--core-dir", required=True)
    a = ap.parse_args()
    sys.exit(dispatch(a.runtime, a.hook, a.root, a.core_dir, sys.stdin.read()))


if __name__ == "__main__":
    main()
