"""L3 review-doc 매칭 전략 후보 A — claude_grep_first (보존, 병합금지).

원본 .claude/hooks/pre-implementation-gate.sh 의 알고리즘:
  find plan_docs -name *.md -mtime -30 | xargs grep -l "Round 1|Round 2|L3 review" | head -1
순수화: snapshot.review_candidates = [{path, content}] (adapter 가 mtime<30d 필터해서 제공)에서
패턴 매칭되는 첫 후보를 found 로 본다.

⚠️ UNRESOLVED: codex_feature_signal 과 algorithm_delta. canonical 미선택 — 사람 결정 대기.
"""

import re

# 기본 리뷰 마커(범용). 프로젝트 특화 패턴은 signals["review_patterns"](profile 주입)로 확장 — 엔진 하드코딩 아님(독립).
_DEFAULT_PATTERN = r"Round 1|Round 2|L3.*[Rr]eview|2라운드|독립.*리뷰"


def _compile(patterns: list):
    """F8a: 패턴을 하나로 join 하지 않고 개별 컴파일한다.

    join 후 단일 컴파일은 profile 의 인라인 글로벌 플래그(예: `(?i)`)가 결합식 중간에 끼면
    Python 3.11+ 에서 're.error: global flags not at the start' 로 전체가 깨진다(전략 크래시→L3 영구 BLOCK).
    개별 컴파일하면 각 패턴 시작의 인라인 플래그는 유효하고, 무효한 개별 패턴 하나는 skip 되어
    default 마커 기반 리뷰 탐지가 유지된다(가용성 우선 — 한 패턴 오류가 게이트 전체를 죽이지 않음)."""
    out = []
    for p in patterns:
        try:
            out.append(re.compile(p, re.IGNORECASE))
        except re.error:
            continue  # 무효한 개별 패턴은 skip — default 패턴은 항상 유효
    return out


def find_l3_review(signals: dict, snapshot: dict) -> dict:
    regexes = _compile([_DEFAULT_PATTERN, *(signals.get("review_patterns") or [])])
    for cand in snapshot.get("review_candidates") or []:
        content = cand.get("content") or ""
        if any(rx.search(content) for rx in regexes):
            return {"found": True, "path": cand.get("path", ""), "strategy": "claude_grep_first"}
    return {"found": False, "path": None, "strategy": "claude_grep_first"}
