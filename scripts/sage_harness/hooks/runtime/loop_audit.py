"""loop_audit — Phase 05 적대적 review-rework 루프(Loop A)의 라운드별 감사 추적.

sage-review 스킬이 호스트(claude/codex)에서 루프를 돌릴 때, 각 라운드(찾기→반박→분류→수정)와
종료를 append-only JSONL 로 남겨 "몇 라운드 돌았고, 무엇을 찾고 무엇이 반증으로 걸러졌고, 어떻게
수렴/차단됐는지"를 사후 추적·재현할 수 있게 한다. override_audit 와 같은 패턴 — `.sage/loop_audit.jsonl`
은 커밋 대상이라 동료·CI·리뷰어가 clone 후에도 루프 이력을 본다.

엔진 모듈(도메인값 0): 횟수·집계·종료 이유는 호출자(스킬/게이트)가 주입하고, 경로/시간/레코드
스키마만 여기서 결정한다. 라이브러리는 permissive recorder — 어휘(CLOSE_REASONS/RESULTS) 강제는
호출 CLI/스킬 레이어가 담당(override.py 가 --gate choices 로 강제하고 override_audit 는 permissive 인 것과 동형).
"""
import json
import os
import time
import uuid

AUDIT_REL = os.path.join(".sage", "loop_audit.jsonl")   # 커밋되는 루프 감사 이력

# 종료 어휘(설계 §3) — 호출자가 close 에 넘기는 표준값. 라이브러리는 강제 아닌 참조용 상수로 노출.
CLOSE_RESULTS = ("APPROVED", "BLOCKED")
CLOSE_REASONS = ("CONVERGED", "DRY", "BUDGET_ITER", "BUDGET_TOK", "BLOCKED_ARCH")


def audit_path(root):
    return os.path.join(root, AUDIT_REL)


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path):
    """JSONL 레코드(dict) 목록. 부재 → []. 견고성(codex S2): 파싱 실패 줄뿐 아니라
    valid-but-non-dict(`42`·`[]`·`"junk"`)도 skip — 소비자(runs/rounds_of/retro/시각화)가 매 레코드에
    .get() 하므로, 비-dict 가 섞이면 AttributeError 크래시. 레코드는 항상 dict 라는 계약을 리더에서 강제."""
    if not os.path.exists(path):
        return []
    out = []
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
    return out


def _malformed_line_count(path):
    """비어있지 않은 줄 중 JSON 파싱 실패 또는 비-dict 인 줄 수(integrity 표면화용 — silent drop 탐지)."""
    if not os.path.exists(path):
        return 0
    bad = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                continue
            if not isinstance(rec, dict):
                bad += 1
    return bad


def read_records(root):
    return _read_jsonl(audit_path(root))


def new_run_id():
    return "rl-" + uuid.uuid4().hex[:12]


def _next_seq(root, run_id):
    """run_id 의 다음 시퀀스 번호 = 현재 기록된 레코드 수(open=0, 이후 append 순 단조 +1).
    라이브러리가 직접 stamp 한다(7차 배치3): 게이트가 seq 연속성을 검산하므로, CLI/라이브러리를 거치지
    않고 JSONL 에 손으로 append 한 레코드는 seq 누락/불연속으로 걸린다.
    **범위 명확화(codex R1b P1)**: 이건 *수기/우회 기록·순서 뒤바뀜·누락* 같은 게으른 우회를 잡는
    **sanity 검사**이지 위변조 방지(tamper-resistance)가 아니다 — seq=레코드 수이므로 파일을 읽어 다음
    정수를 추측해 append 하면 통과한다. 진짜 위변조 내성은 해시체인(7차 이후 하드닝 과제). read-before-write
    지만 CLI 가 이미 orphan 체크로 읽으므로 같은 레이어 비용. 루프당 레코드 수는 작아 O(n) 무시 가능."""
    return sum(1 for r in read_records(root) if r.get("run_id") == run_id)


def open_loop(root, risk, cfg=None, run_id=None, now=None, reviewer_requested=None):
    """루프 시작 기록 → run_id 반환. risk ∈ {L2,L3}(호출자 검증). cfg=적용 설정 스냅샷(profile.pdca.review_loop).
    reviewer_requested=profile 이 의도한 리뷰어 모드(예: cross_model/same_runtime) — 실제값은 close 에 기록,
    불일치(degraded)는 audit_summary 가 파생(7차 배치3)."""
    t = time.time() if now is None else now
    rid = run_id or new_run_id()
    rec = {"event": "loop_open", "run_id": rid, "ts": _iso(t), "epoch": int(t),
           "seq": _next_seq(root, rid), "risk": risk, "cfg": cfg or {}}
    if reviewer_requested is not None:
        rec["reviewer_requested"] = reviewer_requested
    _append(audit_path(root), rec)
    return rid


def record_round(root, run_id, iteration, found, survived, accepted, arch=0, tokens=0, now=None):
    """라운드 1건 기록.
    found=FIND 발견수, survived=REFUTE 생존수, accepted=REWORK 채택수, arch=아키텍처 에스컬레이션수, tokens=누적 토큰.
    seq=append 순 단조 번호(라이브러리 stamp, 수기 위조·순서조작 탐지용 — 7차 배치3)."""
    t = time.time() if now is None else now
    _append(audit_path(root), {"event": "round", "run_id": run_id, "ts": _iso(t), "epoch": int(t),
                               "seq": _next_seq(root, run_id),
                               "iteration": int(iteration), "found": int(found), "survived": int(survived),
                               "accepted": int(accepted), "arch": int(arch), "tokens": int(tokens)})


def close_loop(root, run_id, result, reason, iterations, now=None, reviewer_actual=None):
    """루프 종료 기록. result ∈ CLOSE_RESULTS, reason ∈ CLOSE_REASONS(호출 레이어가 강제).
    reviewer_actual=실제 수행된 리뷰어 모드(예: cross_model/same_runtime) — open 의 reviewer_requested 와
    비교해 audit_summary 가 degraded 를 파생(7차 배치3: cross-model 폴백 침묵 차단)."""
    t = time.time() if now is None else now
    rec = {"event": "loop_close", "run_id": run_id, "ts": _iso(t), "epoch": int(t),
           "seq": _next_seq(root, run_id),
           "result": result, "reason": reason, "iterations": int(iterations)}
    if reviewer_actual is not None:
        rec["reviewer_actual"] = reviewer_actual
    _append(audit_path(root), rec)


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
    위변조 방지가 아닌 게으른 우회 탐지임(다음 정수 추측 append 는 통과 — 해시체인은 7차후, 배치3)."""
    if not seq_list or all(s is None for s in seq_list):
        return None
    return seq_list == list(range(len(seq_list)))


def audit_summary(root):
    """게이트 주입용 결정론 요약(2층 불변식: adapter 가 fs 읽고 core 는 이 dict 만 소비).
    {runs: {run_id: {closed, result, clean, seq_ok, reviewer_requested, reviewer_actual, degraded}}, has_any_records}.
    `clean`(codex 코드 R2-P1): run_id 가 정확히 1회 open + 최대 1회 close 일 때만 True. 재사용/중복 open·
    close 나 고아 close(open 0)는 clean=False → 게이트가 stale/모호 증거로 통과되는 것을 차단.
    `seq_ok`(7차 배치3): 라운드 seq 연속성(False=수기/순서조작, None=레거시 skip). `degraded`: 의도한
    reviewer(open) ≠ 실제 reviewer(close) → cross-model 폴백 침묵 차단."""
    recs = read_records(root)
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
        req, act = e["reviewer_requested"], e["reviewer_actual"]
        # degraded(7차 배치3, codex R1b P1 반영): 의도한 reviewer 가 명시됐는데 실제가 *다르거나*
        # close 시점에 *기록조차 안 됨*(act is None)이면 degraded. 후자 = cross-model 요청이 실제
        # 수행을 확인받지 못한 정황(폴백 의심) → 침묵 통과 차단. closed 인 run 에만 적용(진행중 run 은
        # 아직 actual 미확정이 정상). req 미설정(legacy/미사용)이면 False(오탐 없음).
        e["degraded"] = bool(e["closed"] and req is not None and (act is None or req != act))
        del e["opens"]; del e["closes"]
    return {"runs": summary, "has_any_records": bool(recs)}


def _new_summary_entry():
    return {"closed": False, "result": None, "opens": 0, "closes": 0,
            "reviewer_requested": None, "reviewer_actual": None}


def integrity_issues(root):
    """감사 트레일 구조 무결성 검사 → [문자열] (비면 정상). run_id 는 join key 이므로 무결성이 깨지면
    트레일 자체가 malformed(codex S2 P2). write-시 읽기강제는 append-only 패턴(override_audit 가 uuid4 를
    신뢰하듯)을 깨므로, 무결성은 *체크가능 불변식*으로 소비자(retro S4·시각화 S5)·테스트가 검증한다.

    run_id 계약: 호출자가 open_loop()(또는 new_run_id())로 1회 발급하고 그 id 로만 round/close 한다.
    검출(codex S3/S4 강화): ① loop_open 없는 round/close(orphan) ② loop_open 중복 ③ loop_close 중복
    ④ loop_close 이후의 round/close(종료 후 활동) ⑤ 손상/비-dict 줄(읽기 시 silent drop → 증거 불완전).
    append 순서를 그대로 따라 한 패스로 판정."""
    issues = []
    # ⑤ silent-wrong-evidence(codex S4): _read_jsonl 이 손상/비-dict 줄을 조용히 버려, 요약이 부분
    #    증거를 완전한 것처럼 보일 수 있다. raw 스캔으로 버려진 줄 수를 표면화(잘림/손상 신호).
    dropped = _malformed_line_count(audit_path(root))
    if dropped:
        issues.append(f"손상/비-dict 줄 {dropped}건 — 읽기 시 무시됨(파일 잘림/손상 가능, 감사 증거 불완전 위험)")
    recs = read_records(root)
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
    return issues
