"""session-start-snapshot — canonical core (pure policy, IO 없음, 도메인 기본값 0).

계약: decide(event, snapshot) -> decision  (런타임 중립, 결정론적).
- event: adapter 가 관측한 표준 이벤트 { session_id, now_utc }.
- snapshot: adapter 가 파일시스템에서 관측한 값 { exists(이번 세션 스냅샷 이미 있음?), sha256({정규키: 해시}) }.

이번 세션 06 baseline(존재+내용해시)을 기록할지 결정한다. write-once: 이미 이 세션 스냅샷이 있으면
noop 한다 — resume/재-SessionStart 가 세션 도중 baseline 을 덮으면 그 전 변경이 baseline 에 흡수돼
Stop 훅의 writer-독립 감지에서 사라지기 때문. 06 glob·해시·경로는 전부 adapter 관심사(core 도메인값 0).
"""

CONTRACT_VERSION = "1"


def decide(event: dict, snapshot: dict) -> dict:
    """06 baseline 스냅샷 기록 여부·내용을 결정한다.

    반환: { action: "write"|"noop", record: dict|None }.
    - write: adapter 가 record 를 스냅샷 파일로 직렬화한다.
    - noop: 이미 이 세션 baseline 존재(write-once) → adapter 는 아무것도 안 한다.
    """
    if snapshot.get("exists"):
        return {"action": "noop", "record": None}
    return {"action": "write", "record": {
        "session_id": event.get("session_id", "") or "",
        "taken": event.get("now_utc", "") or "",
        "sha256": snapshot.get("sha256") or {},
    }}
