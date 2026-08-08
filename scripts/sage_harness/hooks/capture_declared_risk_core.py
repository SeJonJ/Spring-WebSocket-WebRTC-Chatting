"""capture-declared-risk — canonical core (pure policy, IO 없음).

SAGE hook 단일소스의 알고리즘 계층. 런타임 입력 추출/출력 렌더/파일IO는 adapter 책임.
계약: decide(event: dict) -> decision: dict  (런타임 중립, now_utc 주어지면 결정론적).

양 런타임(claude/codex) hook 공유 알고리즘
(위험레벨 정규식 2패턴, 세션 sanitize, 2일 cleanup 선언, state 구조).
런타임 차이(env명/로그경로/출력 프로토콜/메시지 텍스트)는 adapter 로 분리됨.
"""

import re

# adapter 계약 버전 — manifest.adapter_contract_version 과 일치해야 함
CONTRACT_VERSION = "1"

# 위험레벨 선언 탐지 — 개발 의도 맥락 동반 시에만 (메타 대화 오탐 회피). 정규식은 정책이라 정규화 금지.
_LEVEL_PATTERN_1 = re.compile(
    r"(?i)\bL([0-3])\s*(으?로|로|레벨|수준|작업|개발|진행|이야|야|입니다|처리|로\s*개발|로\s*진행)"
)
_LEVEL_PATTERN_2 = re.compile(
    r"(?i)(?:risk\s*level|리스크\s*(?:레벨)?|레벨)\s*([0-3])"
)

# 선언 해제 — 레벨을 포함하지 않는다(포착 패턴과 경합 금지). capture 보다 먼저 판정한다.
_CLEAR_PATTERN = re.compile(
    r"(?i)(?:위험도|리스크|risk)\s*선언\s*(?:해제|취소|초기화)|clear\s+risk\s+declaration"
)

# 해제 부정. "해제하지 않을 거예요" 로 안전장치가 꺼지면 오탐 포착보다 나쁘다 —
# 사용자가 명시적으로 반대한 방향으로 게이트를 약화시키는 것이다.
# 해제 구절 **직후**만 본다. 문장 전체를 보면 "L3 아니야 위험도 선언 해제" 처럼 부정어가
# 레벨을 향한 경우까지 해제 거부로 오인해 탈출구를 막는다.
_NEGATION_WINDOW = 12
_NEGATED_AFTER = re.compile(
    r"(?i)^\s*(?:하지\s*마|하지\s*않|하지\s*말|안\s*하|안\s*할|말고|말아|말아라|"
    r"필요\s*없|하면\s*안|은\s*안|는\s*안)"
)

# 문장 분리 — 종결부호를 남긴다(의문부호가 판정 재료다). 소수점·버전 표기(3.5, L3.java)에서
# 쪼개지지 않도록 숫자·영문 사이의 점은 경계로 보지 않는다.
_SENTENCE = re.compile(r"(?:[^.!?…\n]|\.(?=[0-9A-Za-z]))+[.!?…]*")

# 의문·가정 표지 — 문장 어디에 있어도 질문·가정으로 보는 강한 표지.
_HYPOTHETICAL = re.compile(
    r"(?i)\?|만약|가정|친다면|친다고|라고\s*치|예를\s*들|한다면|어떻게\s*되|어떡|"
    r"what\s+if|suppose|hypothetic"
)

# 종결형 의문 어미 — 문장 **끝**에서만 본다. 무경계로 잡으면 "지나가요", "만나요" 같은
# 평서형 동사에 걸려 같은 문장의 정당한 선언까지 버린다(실측).
_QUESTION_ENDING = re.compile(
    r"(?i)(?:나요|가요|습니까|입니까|은가|을까|일까|할까|될까|되나|어때|어떤가)"
    r"\s*[.!?…]*\s*$"
)


def _is_hypothetical(sentence: str) -> bool:
    return bool(_HYPOTHETICAL.search(sentence) or _QUESTION_ENDING.search(sentence))

_CLEANUP_PATTERN = "declared-risk-*.json"
_CLEANUP_OLDER_THAN_SECONDS = 2 * 86400  # 2일


def _sentences(text: str) -> list:
    return [m.group(0) for m in _SENTENCE.finditer(text) if m.group(0).strip()]


def _declared_levels(prompt: str) -> list:
    """선언으로 볼 수 있는 레벨들. 의문·가정 문장의 매치는 버린다.

    모호함은 **선언 시도**의 수로 판정한다. 접미사 없는 단순 언급(`캐시는 L2 유지`,
    `L3.java`, 코드블록 주석)은 선언 시도가 아니므로 세지 않는다 — 세면 개발자 프롬프트에서
    흔한 레벨 언급 하나가 정당한 선언을 통째로 폐기한다(실측).
    """
    levels = []
    for sentence in _sentences(prompt):
        if _is_hypothetical(sentence):
            continue
        levels += [int(m.group(1)) for m in _LEVEL_PATTERN_1.finditer(sentence)]
        levels += [int(m.group(1)) for m in _LEVEL_PATTERN_2.finditer(sentence)]
    return levels


def _clear_requested(prompt: str) -> bool:
    """해제는 포착과 같은 문장 필터를 거친다 — 질문·부정에서 안전장치를 끄지 않는다."""
    for sentence in _sentences(prompt):
        if _is_hypothetical(sentence):
            continue
        for match in _CLEAR_PATTERN.finditer(sentence):
            tail = sentence[match.end():match.end() + _NEGATION_WINDOW]
            if not _NEGATED_AFTER.match(tail):
                return True
    return False


def _sanitize_session(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "nosession")[:64]


def decide(event: dict) -> dict:
    """유저 프롬프트에서 명시적 risk level 선언을 포착할지 결정한다.

    event: { prompt, session_id, now_utc, ... }
    decision: { action: capture|noop, level, session_key, state_file, state, cleanup, exit_code, message_key }
    """
    prompt = event.get("prompt") or ""
    session_key = _sanitize_session(event.get("session_id") or "nosession")
    now_utc = event.get("now_utc")  # adapter 가 실행시각/고정값을 주입 (core는 시간 호출 안 함)

    cleanup = {"pattern": _CLEANUP_PATTERN, "older_than_seconds": _CLEANUP_OLDER_THAN_SECONDS}
    state_file = f"declared-risk-{session_key}.json"

    def _plain(action, level=None, file=None, message_key=None):
        return {
            "kind": "capture_declared_risk",
            "action": action,
            "level": level,
            "session_key": session_key,
            "state_file": file,
            "state": None,
            "cleanup": cleanup,
            "exit_code": 0,
            "message_key": ("risk_declaration_cleared" if action == "clear" else message_key),
        }

    # 해제를 포착보다 먼저 본다. 잘못 잡힌 선언을 지우려는 프롬프트가 다시 선언으로 잡히면
    # 사용자에게 남는 탈출구가 없다.
    if _clear_requested(prompt):
        return _plain("clear", file=state_file)

    levels = _declared_levels(prompt)
    if not levels:
        return _plain("noop")

    # 서로 다른 레벨을 함께 선언하면 선언이 아니라 비교·설명이다. 실측: "L3 개발을 1차로 한후
    # … 다시 L2 로 개발을" 이 max() 때문에 L3 선언으로 잡혀 세션 전체가 묶였다.
    #
    # 기각을 사용자에게 알린다. 조용히 넘기면 선언했다고 믿은 채 진행하게 되고, 포착 확인
    # 메시지의 *부재* 가 유일한 신호가 된다 — 부재는 눈치채기 어렵다. 포착을 넓히는 것이 아니라
    # 기각 사실만 알리므로 오탐 위험은 없다.
    if len(set(levels)) != 1:
        return _plain("noop", message_key="risk_declaration_ambiguous")

    level = levels[0]
    return {
        "kind": "capture_declared_risk",
        "action": "capture",
        "level": f"L{level}",
        "session_key": session_key,
        "state_file": f"declared-risk-{session_key}.json",
        "state": {
            "level": f"L{level}",
            "ts": now_utc,
            "excerpt": prompt[:120].replace("\n", " "),
        },
        "cleanup": cleanup,
        "exit_code": 0,
        "message_key": "risk_declared",
    }
