"""pre-implementation-gate — canonical core (pure, IO-bound gate, 부분추출).

Codex 2R 합의: 공유 risk-gate 만 canonical 추출. "L3 review doc 매칭"은 algorithm_delta(병합금지)
→ find_l3_review 전략 슬롯(claude_grep_first / codex_feature_signal 둘 다 보존, v1 미선택).

계약(2단계 pure core):
  classify_risk(event, profile)                              -> {risk, reason, trigger_sources, file_short}
  decide(event, profile, snapshot, strategy_result)          -> {status, exit_code, risk, message_key, safety_degraded?}
- core 는 fs/time 의존 0. plan 후보(내용)·strategy 실행결과는 adapter 가 snapshot/strategy_result 로 주입.

안전 합의(G1): strategy 미선택(unresolved)이면 L3 review 확인 불가 → BLOCK + override-required + safety_degraded.
키워드/파일패턴 매칭은 case-insensitive(G2 canonical, 더 많은 L3 포착 = 안전 방향).
risk trigger(글롭/키워드)는 profile_bound(G3) — core 에 도메인값 0.
"""

import fnmatch
import re

CONTRACT_VERSION = "1"
_RANK = {"none": -1, "L0": 0, "L1": 1, "L2": 2, "L3": 3}


def _imatch(path: str, glob: str) -> bool:
    return fnmatch.fnmatch(path.lower(), glob.lower())


def _has_kw(content: str, keywords: list) -> bool:
    c = (content or "").lower()
    return any(kw.lower() in c for kw in keywords)


def _classify_one(path: str, content: str, profile: dict) -> tuple:
    """단일 변경의 (risk, reason, trigger_sources) — desktop 은 별도(여기선 분류만)."""
    r = profile.get("risk", {})
    # L0 즉시통과
    for g in r.get("l0_pass_globs", []):
        if _imatch(path, g):
            return ("L0", "문서/plan", ["l0_path"])

    risk, reason, trigger_sources = "none", "", []
    # 사유(reason)는 범용 규칙 참조형(제약 #2 독립). 특정 스택/도메인명 금지 —
    # "어느 매칭 규칙이 발동했는지"만 기술한다. 도메인 명칭은 profile.risk(글롭/키워드)가 정의, core 는 중립.
    for g in r.get("l3_filename_globs", []):
        if _imatch(path, g):
            risk, reason, trigger_sources = "L3", "L3 filename 패턴", ["filename_l3"]
            break
    if risk == "none":
        for g in r.get("l2_path_globs", []):
            if _imatch(path, g):
                risk, reason, trigger_sources = "L2", "L2 소스/설정", ["path_l2"]
                break
    if risk == "none":
        for g in r.get("l1_path_globs", []):
            if _imatch(path, g):
                risk, reason, trigger_sources = "L1", "L1 저위험", ["path_l1"]
                break
    if risk == "none":
        return ("none", "", [])

    # 내용 escalation (L1/L2 → L3, L1 → L2)
    if risk in ("L1", "L2") and _has_kw(content, r.get("l3_content_keywords", [])):
        risk, reason = "L3", reason + " + 내용 L3 키워드"
        trigger_sources.append("content_l3")
    elif risk == "L1" and _has_kw(content, r.get("l2_content_keywords", [])):
        risk, reason = "L2", reason + " + 내용 L2 키워드"
        trigger_sources.append("content_l2")
    return (risk, reason, trigger_sources)


def classify_risk(event: dict, profile: dict) -> dict:
    """changes 중 최고 위험 분류. desktop 직접수정은 risk='DESKTOP_BLOCK'."""
    r = profile.get("risk", {})
    desktop_glob = r.get("desktop_block_glob", "")
    changes = event.get("changes") or []

    l3_kw = r.get("l3_content_keywords", [])
    l0_l3_file = ""   # P2-9: L0 즉시통과 파일이 L3 내용 키워드를 담은 경우(비차단 WARN — 민감정보 점검)

    best = {"risk": "none", "reason": "", "is_l3_filename": False,
            "trigger_sources": [], "file_short": ""}
    for ch in changes:
        path = ch.get("path") or ""
        if desktop_glob and _imatch(path, desktop_glob):
            return {"risk": "DESKTOP_BLOCK", "reason": f"동기화 산출물/금지 경로 직접수정 금지: {path}",
                    "is_l3_filename": False, "declared_l3": False,
                    "trigger_sources": ["desktop_block"], "file_short": path}
        content = ch.get("content") or ""
        risk, reason, sources = _classify_one(path, content, profile)
        # L0 는 내용 escalation 을 안 거치므로(즉시통과) 문서에 숨은 L3 키워드를 놓친다 → 별도 비차단 스캔.
        if risk == "L0" and not l0_l3_file and _has_kw(content, l3_kw):
            l0_l3_file = path
        if _RANK.get(risk, -1) > _RANK.get(best["risk"], -1):
            best = {"risk": risk, "reason": reason,
                    "is_l3_filename": "filename_l3" in sources,
                    "trigger_sources": sources, "file_short": path}
    best["l0_l3_file"] = l0_l3_file

    # 유저 선언 레벨 반영 (effective = max(감지, 선언), 상향만)
    declared = event.get("declared_max")  # "L0".."L3" or None
    declared_l3 = declared == "L3"
    if declared and _RANK.get(declared, -1) > _RANK.get(best["risk"], -1):
        best["risk"] = declared
        best["reason"] = (best["reason"] + " + " if best["reason"] else "") + f"유저 선언 {declared}"
        best["trigger_sources"] = list(best.get("trigger_sources") or []) + [f"declared_{declared.lower()}"]
    best["declared_l3"] = declared_l3
    return best


def _doc_match(docs: list, event: dict) -> str:
    """문서 목록에서 ticket(브랜치 숫자) 매칭 → 없으면 최근(recent=7일 이내) fallback.

    plan/phase 문서 존재 판정의 공통 규칙. docs = [{path, content, recent}].
    (원본 Claude 충실성: ticket 매칭은 전체 대상, fallback 은 -mtime -7 제한.)
    """
    import re
    branch = event.get("branch") or ""
    m = re.search(r"[0-9]+", branch)
    ticket = m.group(0) if m else ""
    if ticket:
        for d in docs:
            if ticket in (d.get("content") or ""):
                return d.get("path", "")
    for d in docs:
        if d.get("recent"):
            return d.get("path", "")
    return ""


def _plan_exists(event: dict, snapshot: dict) -> str:
    """snapshot.plan_files 에서 ticket→recent 매칭(기존 계약 유지)."""
    return _doc_match(snapshot.get("plan_files") or [], event)


def _pdca_cfg(profile: dict):
    """PDCA phase 강제 설정. 비활성(enabled=false 또는 phases 없음)이면 None → 게이트는 기존 동작(하위호환)."""
    p = profile.get("pdca") or {}
    if not p.get("enabled"):
        return None
    if not p.get("phases"):
        return None
    return p


def _missing_pre_impl_phases(event: dict, profile: dict, snapshot: dict, risk: str):
    """구현 전 의무 phase 중 문서가 없는 것 목록. pdca 비활성이면 None(=강제 안 함).

    빈 리스트 = 강제 활성이나 결핍 없음(또는 해당 레벨 요구 phase 없음). 비어있지 않으면 결핍.
    phase 문서 존재는 _doc_match(ticket→recent) 규칙 — plan 존재 판정과 동일.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return None
    required = (cfg.get("pre_implementation_required") or {}).get(risk) or []
    if not required:
        return []
    phase_docs = snapshot.get("phase_docs") or {}
    return [pid for pid in required if not _doc_match(phase_docs.get(pid) or [], event)]


def _glob_base(pattern: str) -> str:
    """glob 메타문자(*?[]) 이전까지의 디렉토리 prefix. 예: plan_docs/06-report/**/*.md → plan_docs/06-report.

    report-write 감지는 fnmatch(`**` 미지원, glob.glob 와 의미 불일치) 대신 base 디렉토리 prefix 로 판정한다.
    """
    parts = []
    for seg in pattern.split("/"):
        if any(ch in seg for ch in "*?[]"):
            break
        parts.append(seg)
    return "/".join(parts)


def _under_dir(path: str, base: str) -> bool:
    p = (path or "").lower().lstrip("./")
    b = (base or "").lower()
    return bool(b) and (p == b or p.startswith(b + "/"))


def _report_gate(event: dict, profile: dict, snapshot: dict):
    """report phase 문서를 쓰는 변경이면 approve phase 의 승인 마커 존재 여부 판정.

    반환: None(비활성/해당없음) | {"approved": bool, "report_phase", "approve_phase"}.
    report/approve phase 미설정이면 None. 06(report) 작성 전 05(approve) APPROVED 강제용.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return None
    report_phase = cfg.get("report_phase") or ""
    approve_phase = cfg.get("approve_phase") or ""
    if not report_phase or not approve_phase:
        return None
    phases = {p.get("id"): p for p in (cfg.get("phases") or [])}
    rglob = (phases.get(report_phase) or {}).get("glob") or ""
    if not rglob:
        return None
    base = _glob_base(rglob)   # base 디렉토리 prefix(=glob.glob 스캔과 일치, fnmatch ** 불일치 회피)
    writing_report = any(_under_dir(ch.get("path") or "", base) for ch in (event.get("changes") or []))
    if not writing_report:
        return None
    marker = (cfg.get("approve_marker") or "APPROVED").lower()
    approve_docs = (snapshot.get("phase_docs") or {}).get(approve_phase) or []
    approved = any(marker in (d.get("content") or "").lower() for d in approve_docs)
    return {"approved": approved, "report_phase": report_phase, "approve_phase": approve_phase}


def _is_writing_report(event, cfg):
    report_phase = cfg.get("report_phase") or ""
    if not report_phase:
        return False
    phases = {p.get("id"): p for p in (cfg.get("phases") or [])}
    rglob = (phases.get(report_phase) or {}).get("glob") or ""
    return bool(rglob) and any(_under_dir(ch.get("path") or "", _glob_base(rglob))
                               for ch in (event.get("changes") or []))


def _acceptance_status_match(line, status):
    needle = re.escape(status.upper())
    return re.search(rf"(?<![A-Z0-9]){needle}(?![A-Z0-9])", line.upper()) is not None


def _cycle_risk(event, profile, snapshot, cfg):
    """06 report event 자체는 L0 문서 변경이라, acceptance 대상 risk 는 cycle 문서에서 보수적으로 추정한다.

    명시 risk 를 찾으면 require_for_risk 에 적용하고, 못 찾으면 unknown 으로 둔다. unknown 은 skip 하지 않는다:
    기존 문서가 risk 라벨을 안 썼다는 이유로 acceptance gate 가 조용히 꺼지는 것을 피하기 위해서다.
    """
    declared = event.get("declared_max")
    if declared in ("L1", "L2", "L3"):
        return declared
    injected = snapshot.get("cycle_risk")
    if injected in ("L1", "L2", "L3"):
        return injected
    phase_docs = snapshot.get("phase_docs") or {}
    for phase in ("00", "01", "02", "03", "04", "05"):
        sel_path = _doc_match(phase_docs.get(phase) or [], event)
        doc = next((d for d in (phase_docs.get(phase) or []) if d.get("path") == sel_path), None) if sel_path else None
        content = (doc or {}).get("content") or ""
        for line in content.splitlines():
            m = re.search(r"(?i)(risk\s*level|risk|위험도)\s*[:：]\s*(L[123])\b", line)
            if m:
                return m.group(2).upper()
    return "unknown"


def _section_table_lines(content, heading_words):
    """주어진 heading 아래의 markdown table line 만 반환. 다음 heading 에서 종료."""
    lines, in_section = [], False
    for raw in (content or "").splitlines():
        stripped = raw.strip()
        if re.match(r"^#{1,6}\s+", stripped):
            title = stripped.lstrip("#").strip().lower()
            if in_section:
                break
            if any(word.lower() in title for word in heading_words):
                in_section = True
            continue
        if in_section and "|" in stripped:
            lines.append(stripped)
    return lines


def _split_md_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if not cells or all(not c for c in cells):
        return []
    if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
        return []
    return cells


def _table_dicts(lines):
    header = None
    rows = []
    for line in lines:
        cells = _split_md_row(line)
        if not cells:
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        row = {header[i]: cells[i] for i in range(min(len(header), len(cells)))}
        row["_raw"] = line
        rows.append(row)
    return rows


def _first_cell(row, names):
    for name in names:
        for key, val in row.items():
            if key != "_raw" and name in key:
                return val
    return ""


def _acceptance_matrix_ids(content):
    rows = _table_dicts(_section_table_lines(content, ["acceptance matrix", "수용", "인수"]))
    ids = []
    for row in rows:
        rid = _first_cell(row, ["id", "acceptance"])
        required = (_first_cell(row, ["required", "필수"]) or "yes").strip().lower()
        if rid and required not in ("no", "false", "n", "optional", "n/a"):
            ids.append(rid.strip())
    return ids


def _acceptance_evidence_rows(content):
    rows = _table_dicts(_section_table_lines(content, ["acceptance evidence", "acceptance evidence review", "수용", "인수"]))
    out = []
    for row in rows:
        rid = _first_cell(row, ["id", "acceptance"])
        status = _first_cell(row, ["status", "상태"])
        if rid or status:
            out.append({"id": rid.strip(), "status": status.strip(), "raw": row.get("_raw", "")})
    return out


def _acceptance_gate(event, profile, snapshot):
    """06 작성 시 04 acceptance evidence 를 검사한다(advisory-first).

    SAGE 의 실패 모드: build/test/review 는 통과했지만 명시 요구사항이 미검증/미구현. 이 gate 는
    판단 자체를 하지 않고 04 문서의 구조화된 상태(PASS/FAIL/NOT TESTED/N/A)만 확인한다.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None or not _is_writing_report(event, cfg):
        return None
    verification = profile.get("verification") or {}
    ac = verification.get("acceptance") if isinstance(verification, dict) else None
    if not isinstance(ac, dict) or not ac.get("enabled"):
        return None
    mode = ac.get("report_gate_enforce") or "off"
    if mode not in ("advisory", "enforce"):
        return None
    required_risks = set(ac.get("require_for_risk") or ["L2", "L3"])
    cycle_risk = _cycle_risk(event, profile, snapshot, cfg)
    if cycle_risk != "unknown" and cycle_risk not in required_risks:
        return None

    statuses = [str(s).upper() for s in (ac.get("statuses") or ["PASS", "FAIL", "NOT TESTED", "N/A"])]
    unresolved = [str(s).upper() for s in (ac.get("unresolved_statuses") or ["FAIL", "NOT TESTED"])]
    phase_docs = snapshot.get("phase_docs") or {}
    docs01 = phase_docs.get("01") or []
    docs04 = phase_docs.get("04") or []
    plan_path = _doc_match(docs01, event)
    plan_doc = next((d for d in docs01 if d.get("path") == plan_path), None) if plan_path else None
    sel_path = _doc_match(docs04, event)
    sel = next((d for d in docs04 if d.get("path") == sel_path), None) if sel_path else None

    def fail(detail):
        return {"ok": False, "mode": mode, "detail": detail}

    if sel is None:
        return fail("cycle 에 해당하는 04 문서를 특정할 수 없음(ticket/recent 미매칭)")
    required_ids = _acceptance_matrix_ids((plan_doc or {}).get("content") or "")
    evidence_rows = _acceptance_evidence_rows(sel.get("content") or "")
    if not required_ids:
        return fail(f"선택된 01 문서({plan_path or '미선택'})에 acceptance matrix ID 없음")
    if not evidence_rows:
        return fail(f"선택된 04 문서({sel_path})에 acceptance evidence table 없음(PASS/FAIL/NOT TESTED/N/A 필요)")
    known_statuses = set(statuses)
    unresolved_lines = []
    seen_ids = set()
    for row in evidence_rows:
        rid = row.get("id") or ""
        status = (row.get("status") or "").upper()
        if rid:
            seen_ids.add(rid)
        if not status or status not in known_statuses:
            unresolved_lines.append(f"{row.get('raw')} (상태값 미인식: {row.get('status')!r})")
        elif status in unresolved:
            unresolved_lines.append(row.get("raw") or f"{rid}: {status}")
    missing_ids = [rid for rid in required_ids if rid not in seen_ids]
    if missing_ids:
        return fail(f"04 acceptance evidence 에 01 matrix required ID 누락: {missing_ids}")
    if unresolved_lines:
        preview = "; ".join(unresolved_lines[:3])
        more = "" if len(unresolved_lines) <= 3 else f"; ... 외 {len(unresolved_lines) - 3}건"
        return fail(f"선택된 04 문서({sel_path})에 미해결 acceptance 존재: {preview}{more}")
    return {"ok": True, "mode": mode, "detail": sel_path}


def _audit_gate(event, profile, snapshot):
    """9.5 — report←approve 에 loop_audit 증거 요건을 더한다(advisory-first, run_id 바인딩).

    반환: None(skip) | {"ok": bool, "mode": "advisory"|"enforce", "detail": str}.
    skip 조건: pdca/review_loop 비활성, flag off/미설정, 또는 06 작성이 아님.
    검사: cycle 05 문서 1개를 _doc_match 로 선택 → 그 동일 문서에서 APPROVED 마커 + `Loop-Run: <id>` 를
    함께 읽고, 주입된 loop_audit.runs[id] 가 closed+APPROVED 인지. (codex 설계 R1~R4: stale 결합 차단.)
    """
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return None
    rl = cfg.get("review_loop") or {}
    if not rl.get("enabled"):
        return None   # 루프 미기대 → 현행 마커-only (오차단 방지)
    mode = rl.get("report_gate_enforce") or "advisory"   # 7차 배치3-5: 기본 off→advisory(루프 켠 프로젝트는 최소 WARN)
    if mode not in ("advisory", "enforce"):
        return None   # 명시 off/무효 → skip(하위호환)
    report_phase = cfg.get("report_phase") or ""
    approve_phase = cfg.get("approve_phase") or ""
    if not report_phase or not approve_phase:
        return None
    if not _is_writing_report(event, cfg):
        return None   # 06 작성이 아님

    # cycle-관련 05 문서 1개 선택(기존 _doc_match: ticket→recent). APPROVED 와 Loop-Run 을 같은 문서에서 읽는다.
    approve_docs = (snapshot.get("phase_docs") or {}).get(approve_phase) or []
    sel_path = _doc_match(approve_docs, event)
    sel = next((d for d in approve_docs if d.get("path") == sel_path), None) if sel_path else None
    la = snapshot.get("loop_audit") or {}
    has_any = bool(la.get("has_any_records"))

    def fail(detail):
        return {"ok": False, "mode": mode, "detail": detail}

    if sel is None:
        return fail("cycle 에 해당하는 05 문서를 특정할 수 없음(ticket/recent 미매칭)")
    content = sel.get("content") or ""
    marker = (cfg.get("approve_marker") or "APPROVED")
    if marker.lower() not in content.lower():
        return fail(f"선택된 05 문서({sel_path})에 {marker} 마커 없음")
    # run_id 는 `review-loop` 가 verbatim 저장(커스텀 --run-id 포함) → 게이트도 비공백 토큰을 그대로 받는다
    # (codex 코드 R1-P1: 협소 charset 이면 rev:123·run/1 같은 합법 run 을 오차단).
    m = re.search(r"(?im)^\s*Loop-Run:\s*(\S+)\s*$", content)
    if not m:
        hint = "audit 기록 자체가 없음 — 루프 미실행 의심" if not has_any else "05 문서에 Loop-Run 미기재"
        return fail(f"선택된 05 문서({sel_path})에 Loop-Run 미기재 ({hint})")
    run_id = m.group(1)
    runs = la.get("runs") or {}
    run = runs.get(run_id)
    if run is None:
        return fail(f"05 가 가리키는 run {run_id!r} 가 audit 에 없음(loop open/close 미기록)")
    if not run.get("clean", True):
        # 재사용/중복 open·close·고아 → 증거 모호(stale 결과로 통과 차단, codex 코드 R2-P1)
        return fail(f"run {run_id!r} 의 audit 이력이 모호(중복/재사용 open·close) — 증거 신뢰 불가")
    if run.get("seq_ok") is False:
        # 7차 배치3-3: seq 불연속/누락 = CLI/라이브러리 우회한 수기 JSONL append 또는 순서 조작.
        return fail(f"run {run_id!r} 의 라운드 seq 불연속/누락 — 수기 기록 또는 순서 조작 의심(감사 증거 신뢰 불가)")
    if not run.get("closed"):
        return fail(f"run {run_id!r} 가 닫히지 않음(루프 미종료)")
    if (run.get("result") or "").upper() != "APPROVED":
        return fail(f"run {run_id!r} 가 result={run.get('result')!r} 로 종료(APPROVED 아님)")
    if run.get("degraded"):
        # 7차 배치3-4: 의도한 reviewer(open) ≠ 실제(close) — cross-model 요청이 same-runtime 으로 폴백된 정황.
        return fail(f"run {run_id!r} reviewer 불일치: 의도={run.get('reviewer_requested')!r} "
                    f"실제={run.get('reviewer_actual')!r} (cross-model 의도 검토 미수행 의심)")
    return {"ok": True, "mode": mode, "detail": run_id}


def decide(event: dict, profile: dict, snapshot: dict, strategy_result) -> dict:
    """risk-gate 판정. strategy_result: None=미선택 / {found:bool, path?} = 선택된 전략 실행결과."""
    c = classify_risk(event, profile)
    risk = c["risk"]

    if risk == "DESKTOP_BLOCK":
        return {"status": "block", "exit_code": 2, "risk": "DESKTOP",
                "message_key": "block_desktop", "reason": c["reason"], "file_short": c["file_short"]}

    # PDCA report←approve 게이트: report phase 문서 작성은 L0(plan_docs)이라 아래 단축 전에 검사.
    # (pdca 비활성이거나 report/approve 미설정 → None → skip, 하위호환)
    rg = _report_gate(event, profile, snapshot)
    if rg is not None and not rg["approved"]:
        return {"status": "block", "exit_code": 2, "risk": "PDCA",
                "message_key": "block_report_without_approval",
                "reason": f"{rg['report_phase']} 작성 전 {rg['approve_phase']} 승인(APPROVED) 필요",
                "file_short": c["file_short"]}

    # Acceptance evidence gate: 04 가 요구사항별 PASS/FAIL/NOT TESTED 를 기록했는지 확인.
    # build/test/lint 통과가 사용자 요구사항 충족을 자동 증명하지 않는 갭을 advisory-first 로 닫는다.
    acg = _acceptance_gate(event, profile, snapshot)
    if acg is not None and not acg["ok"]:
        if acg["mode"] == "enforce":
            return {"status": "block", "exit_code": 2, "risk": "PDCA",
                    "message_key": "block_report_without_acceptance",
                    "reason": f"acceptance evidence 미충족(enforce): {acg['detail']}",
                    "file_short": c["file_short"]}
        return {"status": "warn", "exit_code": 0, "risk": "PDCA",
                "message_key": "warn_report_without_acceptance",
                "reason": f"acceptance evidence 미충족(advisory): {acg['detail']}",
                "file_short": c["file_short"]}

    # 9.5 report←approve audit 증거(F-5): 마커는 있으나 cycle 05 가 가리키는 loop run 이 closed+APPROVED 가
    # 아니면 advisory=WARN / enforce=BLOCK. review_loop 비활성·flag off 면 ag=None → skip(하위호환).
    ag = _audit_gate(event, profile, snapshot)
    if ag is not None and not ag["ok"]:
        if ag["mode"] == "enforce":
            return {"status": "block", "exit_code": 2, "risk": "PDCA",
                    "message_key": "block_report_without_audit",
                    "reason": f"리뷰 루프 audit 증거 미충족(enforce): {ag['detail']}",
                    "file_short": c["file_short"]}
        return {"status": "warn", "exit_code": 0, "risk": "PDCA",
                "message_key": "warn_report_without_audit",
                "reason": f"리뷰 루프 audit 증거 미충족(advisory): {ag['detail']}",
                "file_short": c["file_short"]}

    if risk in ("none", "L0"):
        if c.get("l0_l3_file"):   # P2-9: L0 문서에 L3 내용 키워드 — 비차단 WARN(exit0, 민감정보 노출 점검)
            return {"status": "warn", "exit_code": 0, "risk": risk,
                    "message_key": "warn_l0_l3_content",
                    "reason": "L0 문서/plan 에 L3 내용 키워드 — 민감정보 노출 여부 점검",
                    "file_short": c["l0_l3_file"]}
        return {"status": "ok", "exit_code": 0, "risk": risk, "message_key": None, "reason": c["reason"]}

    # PDCA 의무 phase 강제: 구현 전 필수 phase 결핍 시 L2/L3 BLOCK, L1 WARN.
    # missing=None(pdca 비활성) 또는 [](충족) → falsy → 기존 per-level 로직으로 (하위호환).
    missing = _missing_pre_impl_phases(event, profile, snapshot, risk)
    if missing:
        if risk in ("L2", "L3"):
            return {"status": "block", "exit_code": 2, "risk": risk,
                    "message_key": "block_phase_incomplete", "missing_phases": missing,
                    "reason": c["reason"], "file_short": c["file_short"]}
        return {"status": "warn", "exit_code": 0, "risk": "L1",
                "message_key": "warn_phase_incomplete", "missing_phases": missing,
                "reason": c["reason"], "file_short": c["file_short"]}

    plan_exists = _plan_exists(event, snapshot)

    if risk == "L3":
        # 강신호 + plan 없음 → 하드 블록 (공유)
        content_l3_block = ((profile.get("risk") or {}).get("content_l3_enforce", "warn") == "block"
                            and "content_l3" in (c.get("trigger_sources") or []))
        if (c["is_l3_filename"] or c["declared_l3"] or content_l3_block) and not plan_exists:
            return {"status": "block", "exit_code": 2, "risk": "L3",
                    "message_key": "block_l3_no_plan", "reason": c["reason"], "file_short": c["file_short"]}
        # review doc 확인 = 전략. 미선택이면 확인 불가 → 안전 바닥(BLOCK + override)
        if strategy_result is None:
            return {"status": "block", "exit_code": 2, "risk": "L3",
                    "message_key": "block_l3_strategy_unresolved", "safety_degraded": True,
                    "reason": c["reason"], "file_short": c["file_short"]}
        if strategy_result.get("found"):
            return {"status": "ok", "exit_code": 0, "risk": "L3",
                    "message_key": "ok_l3", "reason": c["reason"], "file_short": c["file_short"]}
        if strategy_result.get("enforce"):
            return {"status": "block", "exit_code": 2, "risk": "L3",
                    "message_key": "block_l3_review_evidence",
                    "reason": strategy_result.get("reason") or c["reason"],
                    "file_short": c["file_short"]}
        return {"status": "warn", "exit_code": 0, "risk": "L3",
                "message_key": "warn_l3_no_review", "reason": c["reason"], "file_short": c["file_short"]}

    if risk == "L2":
        if not plan_exists:
            return {"status": "warn", "exit_code": 0, "risk": "L2",
                    "message_key": "warn_l2_no_plan", "reason": c["reason"], "file_short": c["file_short"]}
        return {"status": "ok", "exit_code": 0, "risk": "L2",
                "message_key": "ok_l2", "reason": c["reason"], "file_short": c["file_short"]}

    # L1 통과
    return {"status": "ok", "exit_code": 0, "risk": "L1", "message_key": None, "reason": c["reason"]}
