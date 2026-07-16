# hooks/strategies — L3 review-doc 매칭 전략 후보 (algorithm_delta, 병합금지)

`pre_implementation_gate` 의 "L3 review doc 매칭"은 두 런타임(claude/codex)이 갈라진
**algorithm_delta**(병합 금지)다. 두 알고리즘을 **둘 다 보존**하되 **canonical 미선택(unresolved)**
상태로 둔다(설계: drift 비병합 — 갈라진 정본은 사람이 선택).

두 전략 모두 도메인값 0(중립). 프로젝트 특화는 `signals` 로 주입한다(엔진 하드코딩 아님, 제약 #2).

- `claude_grep_first.py` — 리뷰 마커 grep 매칭. 기본 마커(Round 1/2, L3 review, 2라운드, 독립 리뷰) +
  `signals["review_patterns"]`(profile 주입)로 확장.
- `codex_feature_signal.py` — feature-signal 토큰 스코어링. 범용 stopword +
  `signals["generic_tokens"]`(profile 주입, 스택특화 토큰)로 확장.
- `cycle_domain_review.py` — SD-8 결정론 전략. 전용 review glob의 frontmatter에서
  current cycle, `round: [1, 2]`, 변경으로 매치된 모든 `domain_ref`를 AND로 검증한다.

**선택**: `profile.risk.l3_review_strategy` 로 둘 중 하나를 canonical 선택한다. 미선택이면
core 는 `strategy_result=None` → L3 review 확인 불가 → 안전 BLOCK(override-required),
manifest `.unresolved` 에 "canonical 사람 결정 필요"로 표기된다.

**다른 프로젝트**: 두 후보 중 선택하거나, 같은 계약(`find_l3_review(signals, snapshot) -> {found, path?}`)을
구현한 자기 전략을 추가해 선택한다.
