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

_CLEANUP_PATTERN = "declared-risk-*.json"
_CLEANUP_OLDER_THAN_SECONDS = 2 * 86400  # 2일


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

    levels = [int(m.group(1)) for m in _LEVEL_PATTERN_1.finditer(prompt)]
    levels += [int(m.group(1)) for m in _LEVEL_PATTERN_2.finditer(prompt)]

    if not levels:
        return {
            "kind": "capture_declared_risk",
            "action": "noop",
            "level": None,
            "session_key": session_key,
            "state_file": None,
            "state": None,
            "cleanup": cleanup,
            "exit_code": 0,
            "message_key": None,
        }

    level = max(levels)
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
