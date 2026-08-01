"""loop_audit — Phase 05 적대적 review-rework 루프(Loop A)의 라운드별 감사 추적.

sage-review 스킬이 호스트(claude/codex)에서 루프를 돌릴 때, 각 라운드(찾기→반박→분류→수정)와
종료를 append-only JSONL 로 남겨 "몇 라운드 돌았고, 무엇을 찾고 무엇이 반증으로 걸러졌고, 어떻게
수렴/차단됐는지"를 사후 추적·재현할 수 있게 한다. override_audit 와 같은 패턴 — `.sage/loop_audit.jsonl`
은 커밋 대상이라 동료·CI·리뷰어가 clone 후에도 루프 이력을 본다.

엔진 모듈(도메인값 0): 횟수·집계·종료 이유는 호출자(스킬/게이트)가 주입하고, 경로/시간/레코드
스키마·run별 strict hash-chain·원자 append만 여기서 결정한다. 라이브러리는 어휘에 대해서만 permissive —
어휘(CLOSE_REASONS/RESULTS) 강제는 호출 CLI/스킬 레이어가 담당한다.
"""
import hashlib
import json
import os
import stat
import time
import uuid
from contextlib import contextmanager

AUDIT_REL = os.path.join(".sage", "loop_audit.jsonl")   # 커밋되는 루프 감사 이력
CHAIN_VERSION = 1
GENESIS = "GENESIS"
_CHAIN_FIELDS = ("chain_version", "prev_hash", "record_hash")

# 종료 어휘(설계 §3) — 호출자가 close 에 넘기는 표준값. 라이브러리는 강제 아닌 참조용 상수로 노출.
CLOSE_RESULTS = ("APPROVED", "BLOCKED")
CLOSE_REASONS = ("CONVERGED", "DRY", "BUDGET_ITER", "BUDGET_TOK", "BLOCKED_ARCH")


class AuditWriteError(RuntimeError):
    """Loop audit cannot be extended without losing its integrity contract."""


def audit_path(root):
    return os.path.join(root, AUDIT_REL)


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _record_hash(record):
    """Canonical SHA-256 for one record, excluding only its stored self-hash."""
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _chain_states(records):
    """Return strict per-run chain states: True, False, or None for legacy-only."""
    states = {}
    previous = {}
    started = set()
    for record in records or []:
        if not isinstance(record, dict):
            continue
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            continue

        has_chain_field = any(field in record for field in _CHAIN_FIELDS)
        if not has_chain_field:
            if run_id in started:
                states[run_id] = False
            else:
                states.setdefault(run_id, None)
            previous[run_id] = record
            continue

        if run_id not in started:
            states[run_id] = True
        started.add(run_id)
        expected_prev = (_record_hash(previous[run_id])
                         if run_id in previous else GENESIS)
        stored_hash = record.get("record_hash")
        valid = (
            type(record.get("chain_version")) is int
            and record.get("chain_version") == CHAIN_VERSION
            and isinstance(record.get("prev_hash"), str)
            and record.get("prev_hash") == expected_prev
            and isinstance(stored_hash, str)
            and len(stored_hash) == 64
            and all(char in "0123456789abcdef" for char in stored_hash)
            and stored_hash == _record_hash(record)
        )
        if not valid:
            states[run_id] = False
        previous[run_id] = record
    return states


def _stamp_record(prior, record):
    stamped = dict(record)
    run_id = stamped.get("run_id")
    same_run = [item for item in prior if item.get("run_id") == run_id]
    stamped["seq"] = len(same_run)
    stamped["chain_version"] = CHAIN_VERSION
    stamped["prev_hash"] = _record_hash(same_run[-1]) if same_run else GENESIS
    stamped["record_hash"] = _record_hash(stamped)
    return stamped


@contextmanager
def _audit_lock(path):
    """OS-owned process lock; process exit releases ownership without stale takeover."""
    lock_path = path + ".lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = None
    backend = None
    try:
        fd = os.open(lock_path, flags, 0o600)
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            backend = "msvcrt"
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
            backend = "fcntl"
    except (ImportError, OSError) as exc:
        if fd is not None:
            os.close(fd)
        raise AuditWriteError(f"loop audit lock acquisition failed: {type(exc).__name__}: {exc}") from exc
    try:
        yield
    finally:
        try:
            if backend == "msvcrt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            elif backend == "fcntl":
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            if fd is not None:
                os.close(fd)


def _parse_bytes(data):
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return [], [f"audit is not valid UTF-8: {exc}"]
    records = []
    issues = []
    for line_no, line in enumerate(lines, 1):
        raw = line.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except Exception:
            issues.append(f"line {line_no}: malformed JSON")
            continue
        if not isinstance(record, dict):
            issues.append(f"line {line_no}: record must be an object")
            continue
        records.append(record)
    return records, issues


def _read_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    return _parse_bytes(b"".join(chunks))


def _open_audit(path, flags):
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError("loop audit must be a regular file")
    return fd


def _read_status(path):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        return [], []
    try:
        with _audit_lock(path):
            if not os.path.lexists(path):
                return [], []
            fd = _open_audit(path, os.O_RDONLY)
            try:
                return _read_fd(fd)
            finally:
                os.close(fd)
    except (AuditWriteError, OSError) as exc:
        return [], [f"audit read failed: {type(exc).__name__}: {exc}"]


def _write_once(fd, payload):
    return os.write(fd, payload)


def _needs_line_separator(fd, size):
    if size <= 0:
        return False
    os.lseek(fd, -1, os.SEEK_END)
    return os.read(fd, 1) != b"\n"


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _audit_lock(path):
        fd = None
        original_size = 0
        attempted_write = False
        try:
            fd = _open_audit(path, os.O_RDWR | os.O_CREAT | os.O_APPEND)
            original_size = os.fstat(fd).st_size
            needs_separator = _needs_line_separator(fd, original_size)
            prior, issues = _read_fd(fd)
            if issues:
                raise AuditWriteError("loop audit contains invalid lines: " + "; ".join(issues[:3]))
            run_id = record.get("run_id")
            if _chain_states(prior).get(run_id) is False:
                raise AuditWriteError(f"run {run_id!r} strict hash-chain is invalid")

            stamped = _stamp_record(prior, record)
            if _chain_states(prior + [stamped]).get(run_id) is False:
                raise AuditWriteError(f"run {run_id!r} strict hash-chain stamping failed")
            separator = b"\n" if needs_separator else b""
            encoded = separator + (json.dumps(stamped, ensure_ascii=False) + "\n").encode("utf-8")
            attempted_write = True
            written = _write_once(fd, encoded)
            if written != len(encoded):
                raise AuditWriteError(f"short append: {written}/{len(encoded)} bytes")
            os.fsync(fd)
            return stamped
        except BaseException as exc:
            rollback_error = None
            if fd is not None and attempted_write:
                try:
                    os.ftruncate(fd, original_size)
                    os.fsync(fd)
                except OSError as rollback_exc:
                    rollback_error = rollback_exc
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if rollback_error is not None:
                raise AuditWriteError(
                    f"loop audit append failed and rollback failed: {rollback_error}") from exc
            if isinstance(exc, AuditWriteError):
                raise
            raise AuditWriteError(f"loop audit append failed: {type(exc).__name__}: {exc}") from exc
        finally:
            if fd is not None:
                os.close(fd)


def _read_jsonl(path):
    """JSONL 레코드(dict) 목록. 부재 → []. 견고성(codex S2): 파싱 실패 줄뿐 아니라
    valid-but-non-dict(`42`·`[]`·`"junk"`)도 skip — 소비자(runs/rounds_of/retro/시각화)가 매 레코드에
    .get() 하므로, 비-dict 가 섞이면 AttributeError 크래시. 레코드는 항상 dict 라는 계약을 리더에서 강제."""
    return _read_status(path)[0]


def read_records(root):
    return _read_jsonl(audit_path(root))


def new_run_id():
    return "rl-" + uuid.uuid4().hex[:12]


def open_loop(root, risk, cfg=None, run_id=None, now=None, reviewer_requested=None):
    """루프 시작 기록 → run_id 반환. risk ∈ {L2,L3}(호출자 검증). cfg=적용 설정 스냅샷(profile.pdca.review_loop).
    reviewer_requested=profile 이 의도한 리뷰어 모드(예: cross_model/same_runtime) — 실제값은 close 에 기록,
    불일치(degraded)는 audit_summary 가 파생(7차 배치3)."""
    t = time.time() if now is None else now
    rid = run_id or new_run_id()
    rec = {"event": "loop_open", "run_id": rid, "ts": _iso(t), "epoch": int(t),
           "risk": risk, "cfg": cfg or {}}
    if reviewer_requested is not None:
        rec["reviewer_requested"] = reviewer_requested
    _append(audit_path(root), rec)
    return rid


def record_round(root, run_id, iteration, found, survived, accepted, arch=0, tokens=0, now=None):
    """라운드 1건 기록.
    found=FIND 발견수, survived=REFUTE 생존수, accepted=REWORK 채택수, arch=아키텍처 에스컬레이션수, tokens=누적 토큰.
    seq=append 순 단조 번호(라이브러리 stamp, 수기 위조·순서조작 탐지용 — 7차 배치3)."""
    t = time.time() if now is None else now
    return _append(audit_path(root), {
        "event": "round", "run_id": run_id, "ts": _iso(t), "epoch": int(t),
        "iteration": int(iteration), "found": int(found), "survived": int(survived),
        "accepted": int(accepted), "arch": int(arch), "tokens": int(tokens),
    })


def close_loop(root, run_id, result, reason, iterations, now=None, reviewer_actual=None):
    """루프 종료 기록. result ∈ CLOSE_RESULTS, reason ∈ CLOSE_REASONS(호출 레이어가 강제).
    reviewer_actual=실제 수행된 리뷰어 모드(예: cross_model/same_runtime) — open 의 reviewer_requested 와
    비교해 audit_summary 가 degraded 를 파생(7차 배치3: cross-model 폴백 침묵 차단)."""
    t = time.time() if now is None else now
    rec = {"event": "loop_close", "run_id": run_id, "ts": _iso(t), "epoch": int(t),
           "result": result, "reason": reason, "iterations": int(iterations)}
    if reviewer_actual is not None:
        rec["reviewer_actual"] = reviewer_actual
    return _append(audit_path(root), rec)


def runs(root):
    """감사 로그의 run_id 목록(loop_open 기준, 시간순)."""
    return [r.get("run_id") for r in read_records(root) if r.get("event") == "loop_open"]


def rounds_of(root, run_id):
    """특정 run_id 의 round 레코드(append 순)."""
    return [r for r in read_records(root)
            if r.get("event") == "round" and r.get("run_id") == run_id]


def close_of(root, run_id):
    """특정 run_id 의 loop_close 레코드(없으면 None — 미종료/진행중)."""
    closes = [r for r in read_records(root)
              if r.get("event") == "loop_close" and r.get("run_id") == run_id]
    return closes[-1] if closes else None


def _seq_ok(seq_list):
    """run 의 레코드 seq 값(append 순) sanity 검산 → True/False/None.
    None = 모두 seq 부재(레거시/구버전 기록) → 검사 skip(하위호환). 일부라도 seq 가 있으면
    정확히 [0,1,...,n-1] 연속이어야 True. 누락(수기 append)·중복·순서조작(재정렬)·레거시+신규 혼합은 False.
    단독 위변조 방지가 아닌 구조 sanity 검사이며, strict hash-chain 검증과 함께 소비한다."""
    if not seq_list or all(s is None for s in seq_list):
        return None
    return seq_list == list(range(len(seq_list)))


def audit_summary(root):
    """게이트 주입용 결정론 요약(2층 불변식: adapter 가 fs 읽고 core 는 이 dict 만 소비).
    {runs: {run_id: {closed, result, clean, seq_ok, chain_ok, reviewer_requested,
    reviewer_actual, degraded}}, has_any_records, file_ok}.
    `clean`(codex 코드 R2-P1): run_id 가 정확히 1회 open + 최대 1회 close 일 때만 True. 재사용/중복 open·
    close 나 고아 close(open 0)는 clean=False → 게이트가 stale/모호 증거로 통과되는 것을 차단.
    `seq_ok`: 라운드 seq 연속성. `chain_ok`: run별 strict hash-chain(True/False, legacy=None).
    `file_ok`: 손상/비-object 줄 없는 원문 파싱 무결성. `degraded`: 의도한 reviewer(open) ≠ 실제
    reviewer(close) → cross-model 폴백 침묵 차단."""
    recs, file_issues = _read_status(audit_path(root))
    chain_states = _chain_states(recs)
    summary = {}
    seqs = {}   # rid -> [seq, ...] (append 순, 모든 이벤트 포함 — seq 연속성 검산용)
    for r in recs:
        rid = r.get("run_id")
        if not rid:
            continue
        seqs.setdefault(rid, []).append(r.get("seq"))
        ev = r.get("event")
        if ev == "loop_open":
            e = summary.setdefault(rid, _new_summary_entry())
            e["opens"] += 1
            if r.get("reviewer_requested") is not None:
                e["reviewer_requested"] = r.get("reviewer_requested")
        elif ev == "loop_close":
            e = summary.setdefault(rid, _new_summary_entry())
            e["closed"] = True
            e["result"] = r.get("result")
            e["closes"] += 1
            if r.get("reviewer_actual") is not None:
                e["reviewer_actual"] = r.get("reviewer_actual")
    for rid, e in summary.items():
        e["clean"] = (e["opens"] == 1 and e["closes"] <= 1)
        e["seq_ok"] = _seq_ok(seqs.get(rid) or [])
        e["chain_ok"] = chain_states.get(rid)
        req, act = e["reviewer_requested"], e["reviewer_actual"]
        # degraded(7차 배치3, codex R1b P1 반영): 의도한 reviewer 가 명시됐는데 실제가 *다르거나*
        # close 시점에 *기록조차 안 됨*(act is None)이면 degraded. 후자 = cross-model 요청이 실제
        # 수행을 확인받지 못한 정황(폴백 의심) → 침묵 통과 차단. closed 인 run 에만 적용(진행중 run 은
        # 아직 actual 미확정이 정상). req 미설정(legacy/미사용)이면 False(오탐 없음).
        e["degraded"] = bool(e["closed"] and req is not None and (act is None or req != act))
        del e["opens"]; del e["closes"]
    return {
        "runs": summary,
        "has_any_records": bool(recs),
        "file_ok": not file_issues,
        "file_issues": file_issues,
    }


def _new_summary_entry():
    return {"closed": False, "result": None, "opens": 0, "closes": 0,
            "reviewer_requested": None, "reviewer_actual": None}


def integrity_issues(root):
    """감사 트레일 구조 무결성 검사 → [문자열] (비면 정상). run_id 는 join key 이므로 무결성이 깨지면
    트레일 자체가 malformed입니다. writer는 락 안에서 원문과 target run 체인을 검증하고, 소비자와
    테스트도 같은 불변식을 재검증합니다.

    run_id 계약: 호출자가 open_loop()(또는 new_run_id())로 1회 발급하고 그 id 로만 round/close 한다.
    검출(codex S3/S4 강화): ① loop_open 없는 round/close(orphan) ② loop_open 중복 ③ loop_close 중복
    ④ loop_close 이후의 round/close(종료 후 활동) ⑤ 손상/비-dict 줄(읽기 시 silent drop → 증거 불완전).
    append 순서를 그대로 따라 한 패스로 판정."""
    recs, file_issues = _read_status(audit_path(root))
    issues = [f"손상/비-dict 감사 줄 — {issue}" for issue in file_issues]
    opens, closes = {}, {}
    for r in recs:
        if r.get("event") == "loop_open":
            opens[r.get("run_id")] = opens.get(r.get("run_id"), 0) + 1
    for rid, n in opens.items():
        if n > 1:
            issues.append(f"run_id {rid!r} loop_open {n}회 중복(uuid 충돌/명시 재사용)")
    for r in recs:
        ev, rid = r.get("event"), r.get("run_id")
        if ev in ("round", "loop_close") and rid not in opens:
            issues.append(f"orphan {ev}: run_id {rid!r} 의 loop_open 없음")
            continue
        if ev in ("round", "loop_close") and closes.get(rid):
            issues.append(f"{ev} after loop_close: run_id {rid!r} 는 이미 종료됨(종료 후 활동)")
        if ev == "loop_close":
            closes[rid] = closes.get(rid, 0) + 1
            if closes[rid] > 1:
                issues.append(f"run_id {rid!r} loop_close {closes[rid]}회 중복")
    # ⑥ 시퀀스 무결성(7차 배치3): seq 누락/불연속/순서조작 — 수기 JSONL append·재정렬 탐지.
    #    라이브러리가 seq 를 stamp 하므로(open=0, append 순 +1), CLI/lib 우회 기록은 seq 부재/불연속으로 걸린다.
    seqs = {}
    for r in recs:
        rid = r.get("run_id")
        if rid:
            seqs.setdefault(rid, []).append(r.get("seq"))
    for rid, sl in seqs.items():
        if _seq_ok(sl) is False:
            issues.append(f"run_id {rid!r} 시퀀스 불연속/누락 {sl} — 수기 기록 또는 순서 조작 의심")
    for rid, state in _chain_states(recs).items():
        if state is False:
            issues.append(f"run_id {rid!r} strict hash-chain 불일치 — 감사 레코드 수정/누락/순서 조작 의심")
    return issues
