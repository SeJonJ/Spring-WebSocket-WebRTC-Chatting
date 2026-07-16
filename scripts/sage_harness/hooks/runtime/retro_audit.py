"""retro_audit — Loop C(`sage retro --check`) 성공 증거의 append-only 감사 추적.

`sage retro --check` 는 host 가 **스스로 실행해야만** 효력이 있다 — 실행을 건너뛰고 06 문서에
"retro 완료"라 적어도 지금까지는 아무것도 막지 못했다(4차 테스트 F-5 와 같은 결함 클래스: 게이트가
마커만 검사하고 실제 프로세스 가동은 검사 안 함). 이 모듈은 `--check` 성공 시점을 `.sage/retro_audit.jsonl`
에 기록해, Stop 훅(`retro_gate` 정책)이 "이 run 이 실제로 check 를 통과했는지"를 사후 확인할 수 있게 한다.

loop_audit.py 와 같은 패턴(2층 불변식): 이 모듈은 stdlib 만 쓰는 순수 유틸이라 hook 런타임(의존성 0)과
`sage` CLI 패키지(`sage/commands/retro.py::_load_retro_audit()`) 양쪽에서 동적 import 로 공유된다.
"""
import hashlib
import json
import os
import time

AUDIT_REL = os.path.join(".sage", "retro_audit.jsonl")   # 커밋되는 retro 게이트 감사 이력

EVENT_CHECK_OK = "retro_check_ok"          # `sage retro --check` 통과(retro.py 가 기록)
EVENT_CHECK_MISSING = "retro_check_missing"  # 06 작성 세션이 retro --check 없이 종료(Stop 훅이 기록)
EVENT_CHECK_SKIPPED = "retro_check_skipped"  # 이번 run 은 vault 노트 생략(`retro --no-vault`) → --check 대상 없음
_EVENTS = (EVENT_CHECK_OK, EVENT_CHECK_MISSING, EVENT_CHECK_SKIPPED)
_STATE = {EVENT_CHECK_OK: "ok", EVENT_CHECK_MISSING: "missing", EVENT_CHECK_SKIPPED: "skipped"}


def audit_path(root):
    return os.path.join(root, AUDIT_REL)


def _iso(epoch=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch if epoch is not None else time.time()))


def digest_of(text):
    """전체 SHA-256(잘라쓰지 않음). **감사 트레일** 용도다 — check 통과 시점에 어떤 노트 내용이
    통과했는지를 기록해 사후에 확인·재현할 수 있게 한다. 게이트 판정 시점(Stop)에 현재 노트를 다시
    읽어 digest 를 재대조하지는 **않는다**: check 이후 사람이 노트를 더 다듬는 것은 정상 흐름이라,
    엄격 재대조는 정당한 편집을 '미확인'으로 오판해 잘못 block 하게 된다(codex 구현리뷰 2R P2 반영).
    파일 자체(.sage/retro_audit.jsonl) 위변조를 막는 보안 경계도 아니다(loop_audit.jsonl 과 동일 신뢰
    모델 — 커밋 이력으로 사후 감사)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_records_status(root):
    """(status, records) — status ∈ {"absent","unreadable","ok"}. 파싱 실패·비-dict 줄은 skip.

    - absent: 감사파일이 (심링크 포함) 아예 없음 → 정말 기록이 없는 것(안전하게 '미완료 없음' 판정 가능).
    - unreadable: 경로는 존재하나(디렉토리·깨진 심링크·권한없음·비-UTF-8) 파일로 못 읽음 → **미완료 없음이
      아니라 신뢰불가**. doctor 는 이 상태를 '없음' 으로 오보하면 안 된다(codex 구현리뷰 4R P1).
    - ok: 정상 읽음(records 는 빈 리스트일 수도 있음 = 진짜 비었음)."""
    path = audit_path(root)
    if not os.path.lexists(path):   # lexists: 깨진 심링크도 존재로 본다(exists 는 False → absent 오판)
        return ("absent", [])
    if not os.path.isfile(path):    # 디렉토리·깨진 심링크 등 = 존재하나 파일 아님
        return ("unreadable", [])
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except (OSError, UnicodeError):
        return ("unreadable", [])
    return ("ok", out)


def read_records(root):
    """JSONL 레코드(dict) 목록. 읽기 측은 절대 크래시하지 않는다(부재/디렉토리/권한/비-UTF-8 전부 → []).
    Stop 훅이 소비자이므로 감사파일이 손상돼도 컴플라이언스 리포트 전체가 죽으면 안 된다(fail-open).
    쓰기 측(record_check)은 반대로 실패 시 예외를 전파해 `--check` 를 fail-closed 로 만든다.
    상태(신뢰불가 vs 진짜 비었음)를 구분해야 하는 소비자(doctor)는 read_records_status 를 쓴다."""
    return read_records_status(root)[1]


def record_check(root, run_id, note_path, note_text, now=None):
    """`sage retro --check` 성공 시 호출자(retro.py)가 append. 반환: 기록된 record dict.
    호출자는 이 함수가 예외를 던지면(디스크 쓰기 실패 등) `--check` 자체를 실패로 처리해야 한다 —
    기록되지 않은 성공은 게이트가 못 보는 성공과 같다(codex 설계리뷰 1R P1)."""
    rec = {"event": EVENT_CHECK_OK, "run_id": run_id, "note_path": note_path,
           "digest": digest_of(note_text), "ts": _iso(now)}
    _append(audit_path(root), rec)
    return rec


def record_missing(root, run_id, note_path=None, now=None):
    """06 작성 세션이 `sage retro --check` 없이 종료됐음을 append(Stop 훅이 호출). **상태변화 시에만**
    기록한다 — 이미 최신 상태가 missing 이면 재기록하지 않아 매 Stop 마다 파일이 불어나는 것을 막는다.
    반환: 기록했으면 record dict, 이미 missing 이면 None. best-effort(호출자가 예외를 삼켜도 됨 —
    이 기록 실패가 컴플라이언스 리포트나 세션을 막으면 안 된다)."""
    if run_id and latest_state(root, run_id) == "missing":
        return None
    rec = {"event": EVENT_CHECK_MISSING, "run_id": run_id, "note_path": note_path, "ts": _iso(now)}
    _append(audit_path(root), rec)
    return rec


def record_skip(root, run_id, reason=None, now=None):
    """이번 run 이 vault 노트를 생략함(`sage retro --no-vault`)을 append(retro.py 가 호출). retro_note 가
    profile 에 켜져 있어도 특정 run 만 노트를 안 쓸 때, 게이트가 없는 노트의 --check 를 요구해 false BLOCK
    하는 걸 막는다(--no-vault↔enforce 충돌 해소). reason 은 감사 추적용 사유("no_vault"). **상태변화 시에만**
    기록(이미 최신이 skipped 면 skip). 반환: 기록했으면 record dict, 이미 skipped 면 None. best-effort."""
    if not run_id or latest_state(root, run_id) == "skipped":
        return None
    rec = {"event": EVENT_CHECK_SKIPPED, "run_id": run_id, "ts": _iso(now)}
    if reason:
        rec["reason"] = reason
    _append(audit_path(root), rec)
    return rec


def summarize(records):
    """records → {run_id: {state, checked, note_path, digest, ts}} — run_id 당 **가장 최근** 이벤트.
    append-only 라 리스트 순서 = 시간 순서. 재검사·재종료로 상태가 뒤집혀도 마지막 이벤트가 유효하다.
    `checked` = (state=='ok') 편의 필드(기존 소비자 호환 — skipped 는 check 통과가 아니므로 False).
    게이트는 checked(ok) 또는 state=='skipped'(--no-vault) 를 통과로 본다(hook_runtime 축약부). 순수 함수."""
    summary = {}
    for r in records:
        ev = r.get("event")
        rid = r.get("run_id")
        if ev not in _EVENTS or not rid:
            continue
        summary[rid] = {"state": _STATE[ev], "checked": ev == EVENT_CHECK_OK,
                        "note_path": r.get("note_path"), "digest": r.get("digest"), "ts": r.get("ts")}
    return summary


def audit_summary(root):
    """{run_id: 최신상태...}. Stop 훅 소비자용(fail-open — 읽기 불가면 빈 dict). 신뢰불가와 진짜 비었음을
    구분해야 하는 doctor 는 audit_summary_status 를 쓴다."""
    return summarize(read_records(root))


def audit_summary_status(root):
    """(status, summary) — read 상태를 보존한 요약. doctor 가 'unreadable' 을 '미완료 없음' 으로
    오보하지 않도록(codex 구현리뷰 4R P1)."""
    status, records = read_records_status(root)
    return status, summarize(records)


def latest_state(root, run_id):
    """run_id 의 최신 상태 문자열('ok'|'missing') 또는 None(기록 없음). record_missing 의 상태변화 판정용."""
    return audit_summary(root).get(run_id, {}).get("state")
