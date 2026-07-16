"""L3 review-doc 매칭 전략 후보 B — codex_feature_signal (보존, 병합금지).

원본 .codex/hooks/pre-implementation-gate.sh 의 알고리즘:
  branch/plan/changed-path 를 토큰화 → generic 토큰 제거 → 후보 plan 문서의 토큰 겹침으로 점수화,
  feature signal 이 충분히 겹치는 후보를 review 로 본다 (grep-first 보다 정교).
순수화: signals(tickets/plan/files 토큰) + snapshot.review_candidates 로 점수 최고 후보 선택.

⚠️ UNRESOLVED: claude_grep_first 와 algorithm_delta. canonical 미선택 — 사람 결정 대기.
"""

import re

# 범용 stopword(스택 무관) — feature signal 로 보기엔 너무 흔한 토큰.
# 스택특화 토큰(프레임워크/언어명 등)은 signals["generic_tokens"](profile 주입)로 확장 — 엔진 하드코딩 아님(독립).
GENERIC_SIGNAL_TOKENS = {
    "src", "main", "test", "static", "service", "controller", "config",
    "json", "true", "false", "plan", "plans", "docs", "base", "design", "review",
}


def _tokens(value: str) -> set:
    parts = re.split(r"[^A-Za-z0-9가-힣]+", value or "")
    return {p.lower() for p in parts if len(p) >= 3}


def _specific(value: str, stop: set) -> set:
    return {t for t in _tokens(value) if t not in stop}


def find_l3_review(signals: dict, snapshot: dict) -> dict:
    stop = GENERIC_SIGNAL_TOKENS | {t.lower() for t in (signals.get("generic_tokens") or [])}
    want = set()
    for key in ("tickets", "plan", "files"):
        want |= set(signals.get(key) or [])
    if not want:
        return {"found": False, "path": None, "strategy": "codex_feature_signal"}

    best, best_score = None, 0
    for cand in snapshot.get("review_candidates") or []:
        have = _specific(cand.get("content") or "", stop) | _specific(cand.get("path") or "", stop)
        score = len(want & have)
        if score > best_score:
            best, best_score = cand.get("path", ""), score
    if best and best_score >= 1:
        return {"found": True, "path": best, "score": best_score, "strategy": "codex_feature_signal"}
    return {"found": False, "path": None, "strategy": "codex_feature_signal"}
