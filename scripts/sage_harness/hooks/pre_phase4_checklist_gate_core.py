"""pre-phase4-checklist-gate — canonical core (pure, fs/time 의존 0).

IO-bound gate 일반형 (Codex 2R 합의): 2단계.
  1. plan_reads(event, profile)            -> 읽어야 할 globs/exact (base 추출 포함)
  2. (adapter 가 fs_snapshot 생성)
  3. decide(event, profile, snapshot)      -> decision (block|warn|ok|skip)
core 는 fs/time 에 의존하지 않는다. 모든 IO 는 adapter 가 snapshot 으로 주입.

양 런타임(claude/codex) hook 공유 알고리즘
(suffix 반복제거 base 추출, exact우선+prefix양방향 find_match, 미완료 체크박스 스캔, gate 판정).
algorithm_delta 없음. 차이 = structural_io_adapter + output_adapter + token_adapter + profile_bound.
"""

import fnmatch
import os
import re

CONTRACT_VERSION = "1"

# PDCA phase 산출물 네이밍 = SAGE-PDCA 방법론 규약(framework 기본, 특정 프로젝트 정체성 아님). profile.suffixes 로 override.
# (phase4_trigger_glob 의 04-analyze 기본값도 동일 — SAGE PDCA phase 구조. 다른 PDCA 미사용 프로젝트는 profile 로 교체)
DEFAULT_SUFFIXES = [
    "_backend_eval", "_frontend_eval", "_external_eval", "_qa_eval",
    "_backend_feedback", "_frontend_feedback", "_external_feedback", "_qa_feedback",
    "-gap", "_gap", "-analysis", "_analysis", "-analyze", "_analyze",
    "_eval", "_feedback", "_plan", "_report",
]

_UNCHECKED_RE = re.compile(r"^\s*-\s*\[\s\]")


def _stem(path: str) -> str:
    b = path.rsplit("/", 1)[-1]
    return b[:-3] if b.endswith(".md") else b


def _base_from(stem: str, suffixes: list) -> str:
    base = stem
    changed = True
    while changed:
        changed = False
        for suf in suffixes:
            if base.endswith(suf) and len(base) > len(suf):
                base = base[: -len(suf)]
                changed = True
    return base


def _dir_of(glob: str) -> str:
    return glob[: -len("/*.md")] if glob.endswith("/*.md") else os.path.dirname(glob)


def _trigger_path(event, trigger_glob):
    for ch in (event.get("changes") or []):
        p = ch.get("path") or ""
        if p and fnmatch.fnmatch(p, trigger_glob):
            return p
    return None


def plan_reads(event: dict, profile: dict) -> dict:
    """트리거된 04-analyze 변경에서 feature base + 읽을 후보(globs/exact)를 산출."""
    trigger = profile.get("phase4_trigger_glob", "*plan_docs/04-analyze/*.md")
    suffixes = profile.get("suffixes") or DEFAULT_SUFFIXES
    targets = profile.get("checklist_scan_targets") or []

    four = _trigger_path(event, trigger)
    if not four:
        return {"base": None, "globs": [], "exact": []}

    base = _base_from(_stem(four), suffixes)
    globs = [t["glob"] for t in targets]
    exact = [f"{_dir_of(t['glob'])}/{base}.md" for t in targets]
    return {"base": base, "globs": globs, "exact": exact}


def _find_match(glob: str, base: str, glob_results: dict):
    """exact 우선 → prefix 양방향 (원본 find_match 재현). 경로는 root-상대."""
    cands = glob_results.get(glob, [])
    exact = f"{_dir_of(glob)}/{base}.md"
    if exact in cands:
        return exact
    for c in sorted(cands):
        cs = _stem(c)
        if base == cs or base.startswith(cs) or cs.startswith(base):
            return c
    return None


def decide(event: dict, profile: dict, snapshot: dict) -> dict:
    """snapshot(미리 읽은 glob 결과 + 파일 내용)으로 게이트 판정.

    decision: { kind, status(block|warn|ok|skip), exit_code, base, total_unchecked, evidence[], message_key }
    """
    trigger = profile.get("phase4_trigger_glob", "*plan_docs/04-analyze/*.md")
    suffixes = profile.get("suffixes") or DEFAULT_SUFFIXES
    targets = profile.get("checklist_scan_targets") or []
    glob_results = snapshot.get("glob_results") or {}
    files = snapshot.get("files") or {}

    four = _trigger_path(event, trigger)
    if not four:
        return {"kind": "phase4_gate", "status": "skip", "exit_code": 0,
                "base": None, "total_unchecked": 0, "evidence": [], "message_key": None}

    base = _base_from(_stem(four), suffixes)

    total_unchecked = 0
    evidence = []
    impl_match = None
    for t in targets:
        label, glob = t["label"], t["glob"]
        m = _find_match(glob, base, glob_results)
        if t.get("is_impl"):
            impl_match = m
        if not m:
            continue
        text = files.get(m)
        read_error = (m not in files) or (text is None)
        items = []
        if not read_error:
            for i, line in enumerate(text.splitlines(), 1):
                if _UNCHECKED_RE.match(line):
                    items.append({"line": i, "text": line.strip()})
        if items or read_error:
            total_unchecked += len(items)
            ev = {"label": label, "file": m, "unchecked": items}
            if read_error:
                ev["read_error"] = True  # 추적용 — block 판정엔 미반영(원본 동작 유지)
            evidence.append(ev)

    if total_unchecked > 0:
        return {"kind": "phase4_gate", "status": "block", "exit_code": 2,
                "base": base, "total_unchecked": total_unchecked,
                "evidence": evidence, "message_key": "gate_block"}
    if impl_match is None:
        return {"kind": "phase4_gate", "status": "warn", "exit_code": 0,
                "base": base, "total_unchecked": 0,
                "evidence": evidence, "message_key": "gate_warn_no_impl"}
    return {"kind": "phase4_gate", "status": "ok", "exit_code": 0,
            "base": base, "total_unchecked": 0,
            "evidence": evidence, "message_key": "gate_ok"}
