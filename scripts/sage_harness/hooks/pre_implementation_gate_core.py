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

import cycle_binding

CONTRACT_VERSION = "2"   # EH-7: decide() 가 cycle_stem/cycle_source/cycle_stem_declared 를 싣고,
                         # 어댑터가 선언 사용을 감사해야 한다. 낡은 어댑터 + 새 core 조합은 스탬프만
                         # 하고 기록을 못 해 무감사 통과가 되므로 STALE 로 잡는다.
_RANK = {"none": -1, "L0": 0, "L1": 1, "L2": 2, "L3": 3}
_STRUCTURED_LABEL_EMPHASIS_RE = re.compile(
    r"(?P<mark>\*{1,3}|_{1,3})(?P<label>Final\s+Status|Loop-Run|Risk\s+Level|Risk|위험도)"
    r"(?P<colon>\s*[:：]?)(?P=mark)",
    re.IGNORECASE,
)
_RISK_LABEL_CANDIDATE_RE = re.compile(r"(?i)(risk\s*level|\brisk\b|위험도).*[：:]")


def _imatch(path: str, glob: str) -> bool:
    return fnmatch.fnmatch(path.lower(), glob.lower())


def _has_kw(content: str, keywords: list) -> bool:
    c = (content or "").lower()
    return any(kw.lower() in c for kw in keywords)


def _classify_one(path: str, content: str, profile: dict) -> tuple:
    """단일 변경의 (risk, reason, trigger_sources) — desktop 은 별도(여기선 분류만)."""
    r = profile.get("risk", {})
    l0_excluded = any(_imatch(path, g) for g in r.get("l0_exclude_globs", []))
    # L0 즉시통과. Domain/explicit exclusion 은 동일 higher-risk path rule로 계속 분류한다.
    if not l0_excluded:
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
    if risk == "none" and l0_excluded:
        # validate/compiler가 orphan exclusion을 차단하지만, pure core도 malformed runtime
        # profile을 L0/none으로 하향하지 않는다.
        return ("L3", "L0 exclusion 상위 위험도 결속 누락", ["l0_excluded", "invalid_profile"])
    if risk == "none":
        return ("none", "", [])
    if l0_excluded:
        trigger_sources.append("l0_excluded")

    # 내용 escalation (L1/L2 → L3, L1 → L2). Filename으로 이미 L3인
    # change도 content provenance는 보존해 감사/compound gate 입력이 정확해야 한다.
    if _has_kw(content, r.get("l3_content_keywords", [])):
        risk = "L3"
        reason += " + 내용 L3 키워드"
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
        elif risk != "none" and risk == best["risk"]:
            # Compound changes can reach the same rank through different controls.
            # Keep every security-relevant provenance instead of letting the first
            # same-rank change mask a later filename/content L3 trigger.
            best["trigger_sources"] = list(dict.fromkeys([*best["trigger_sources"], *sources]))
            if "filename_l3" in sources and not best["is_l3_filename"]:
                best["is_l3_filename"] = True
                best["file_short"] = path
                best["reason"] = reason
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


def _cycle_binding(event, profile, snapshot):
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return None
    return cycle_binding.resolve(event, snapshot, cfg)


def _cycle_doc(docs, binding):
    if not binding or binding.get("error"):
        return None, (binding or {}).get("error") or "cycle binding unavailable"
    return cycle_binding.select_document(docs, binding["stem"])


def _is_phase_write(event, cfg):
    patterns = [item.get("glob") or "" for item in (cfg.get("phases") or [])]
    return any(cycle_binding.matches_glob(change.get("path") or "", pattern)
               for change in (event.get("changes") or []) for pattern in patterns if pattern)


def _changed_phase_ids(event, cfg):
    changed = set()
    for phase in cfg.get("phases") or []:
        pid, pattern = str(phase.get("id") or ""), phase.get("glob") or ""
        if pid and pattern and any(cycle_binding.matches_glob(change.get("path") or "", pattern)
                                   for change in (event.get("changes") or [])):
            changed.add(pid)
    return changed


def _plan_exists(event: dict, snapshot: dict) -> str:
    """snapshot.plan_files 에서 ticket→recent 매칭(기존 계약 유지)."""
    return _doc_match(snapshot.get("plan_files") or [], event)


def _bound_plan_exists(event, profile, snapshot):
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return _plan_exists(event, snapshot)
    binding = cycle_binding.resolve(event, snapshot, cfg)
    if binding.get("error"):
        return ""
    return binding["stem"] if cycle_binding.any_document(snapshot.get("plan_files") or [], binding["stem"]) else ""


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
    phase 문서 존재는 path basename + Cycle-Stem exact binding으로 판정한다.

    결핍 판정은 "문서가 없다" 와 "다른 사이클을 보고 있다" 를 구분하지 못한다. 어느 쪽인지는
    stem 의 출처가 알려주므로, 안내는 decide() 가 스탬프한 cycle_source 로 분기한다.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None:
        return None
    required = (cfg.get("pre_implementation_required") or {}).get(risk) or []
    if not required:
        return []
    phase_docs = snapshot.get("phase_docs") or {}
    binding = cycle_binding.resolve(event, snapshot, cfg)
    if binding.get("error"):
        return ["cycle-binding"]
    missing = []
    for pid in required:
        _doc, error = cycle_binding.select_document(phase_docs.get(pid) or [], binding["stem"])
        if error:
            missing.append(pid)
    return missing


def _final_status(content):
    """Read one anchored status declaration outside Markdown code fences."""
    statuses = []
    for raw in _non_fenced_lines(content):
        line = _structured_declaration_line(raw)
        match = re.fullmatch(r"Final\s+Status\s*:\s*([A-Za-z][A-Za-z0-9_-]*)", line, re.IGNORECASE)
        if match:
            statuses.append(match.group(1).upper())
    if len(statuses) != 1:
        return None, f"Final Status declaration must appear exactly once (found {len(statuses)})"
    return statuses[0], None


def _non_fenced_lines(content):
    yield from cycle_binding.non_fenced_lines(content)


def _structured_line(raw):
    """Remove Markdown emphasis around a governance label, preserving its value."""
    return _STRUCTURED_LABEL_EMPHASIS_RE.sub(
        lambda match: f"{match.group('label')}{match.group('colon')}", raw or "")


def _structured_declaration_line(raw):
    """Normalize label emphasis and one whole-declaration emphasis wrapper."""
    line = _structured_line(raw).strip()
    for marker in ("***", "___", "**", "__", "*", "_"):
        if len(line) > len(marker) * 2 and line.startswith(marker) and line.endswith(marker):
            return line[len(marker):-len(marker)].strip()
    return line


def _parse_risk_declaration(raw):
    """Return L1/L2/L3, unknown for risk-like malformed text, or None when unrelated."""
    line = _structured_declaration_line(raw)
    label = re.search(r"(?i)(risk\s*level|risk|위험도)\s*[:：]", line)
    if label:
        match = re.search(r"(?i)(risk\s*level|risk|위험도)\s*[:：]\s*(L[123])\b", line)
        return match.group(2).upper() if match else "unknown"
    if _RISK_LABEL_CANDIDATE_RE.search(line):
        return "unknown"
    return None


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
    if not _is_writing_report(event, cfg):
        return None
    binding = cycle_binding.resolve(event, snapshot, cfg)
    if binding.get("error"):
        return {"approved": False, "report_phase": report_phase, "approve_phase": approve_phase,
                "detail": binding["error"]}
    marker = (cfg.get("approve_marker") or "APPROVED").upper()
    approve_docs = (snapshot.get("phase_docs") or {}).get(approve_phase) or []
    selected, error = cycle_binding.select_document(approve_docs, binding["stem"])
    if error:
        return {"approved": False, "report_phase": report_phase, "approve_phase": approve_phase,
                "detail": error}
    status, status_error = _final_status(selected.get("content") or "")
    approved = status_error is None and status == marker
    detail = (selected.get("path") if approved else
              f"{selected.get('path')} Final Status 오류: {status_error or f'{status!r} != {marker!r}'}")
    return {"approved": approved, "report_phase": report_phase, "approve_phase": approve_phase,
            "detail": detail, "cycle_stem": binding["stem"]}


def _is_writing_report(event, cfg):
    report_phase = cfg.get("report_phase") or ""
    if not report_phase:
        return False
    phases = {str(p.get("id") or ""): p for p in (cfg.get("phases") or [])}
    rglob = (phases.get(str(report_phase)) or {}).get("glob") or ""
    return bool(rglob) and any(cycle_binding.matches_glob(ch.get("path") or "", rglob)
                               for ch in (event.get("changes") or []))


def _acceptance_status_match(line, status):
    needle = re.escape(status.upper())
    return re.search(rf"(?<![A-Z0-9]){needle}(?![A-Z0-9])", line.upper()) is not None


def _cycle_risk(event, profile, snapshot, cfg):
    """06 report event 자체는 L0 문서 변경이라, acceptance 대상 risk 는 cycle 문서에서 보수적으로 추정한다.

    명시 risk 를 찾으면 require_for_risk 에 적용하고, 못 찾으면 unknown 으로 둔다. unknown 은 skip 하지 않는다:
    기존 문서가 risk 라벨을 안 썼다는 이유로 acceptance gate 가 조용히 꺼지는 것을 피하기 위해서다.
    """
    rank = {"L1": 1, "L2": 2, "L3": 3}
    risks = []
    for value in (event.get("declared_max"), snapshot.get("cycle_risk")):
        if value is None:
            continue
        normalized = str(value).upper()
        if normalized not in rank:
            return "unknown"
        risks.append(normalized)
    binding = cycle_binding.resolve(event, snapshot, cfg)
    if binding.get("error"):
        return "unknown"
    phase_docs = snapshot.get("phase_docs") or {}
    for phase in ("00", "01", "02", "03", "04", "05"):
        docs = phase_docs.get(phase) or []
        matching = [doc for doc in docs
                    if cycle_binding.path_stem(doc.get("path") or "") == binding["stem"]]
        if not matching:
            continue
        doc, error = cycle_binding.select_document(docs, binding["stem"])
        if error:
            return "unknown"
        content = (doc or {}).get("content") or ""
        for raw in _non_fenced_lines(content):
            parsed = _parse_risk_declaration(raw)
            if parsed is None:
                continue
            if parsed == "unknown":
                return "unknown"
            risks.append(parsed)
    return max(risks, key=rank.get) if risks else "unknown"


def _section_table_lines(content, heading_words):
    """주어진 heading 아래의 markdown table line 만 반환. 다음 heading 에서 종료."""
    lines, in_section = [], False
    for raw in _non_fenced_lines(content):
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
    def normalized(value):
        return re.sub(r"[^a-z0-9가-힣]", "", (value or "").lower())

    for name in names:
        target = normalized(name)
        for key, val in row.items():
            if key != "_raw" and normalized(key) == target:
                return val
    for name in names:
        for key, val in row.items():
            if key != "_raw" and name in key:
                return val
    return ""


_ACCEPTANCE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _acceptance_id(value):
    raw = (value or "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == "`":
        raw = raw[1:-1].strip()
    return raw if _ACCEPTANCE_ID_RE.fullmatch(raw) else ""


def _acceptance_matrix(content):
    rows = _table_dicts(_section_table_lines(content, ["acceptance matrix", "수용", "인수"]))
    all_ids, required_ids, invalid_ids = [], [], []
    for row in rows:
        raw_id = _first_cell(row, ["id", "acceptance"])
        rid = _acceptance_id(raw_id)
        required = (_first_cell(row, ["required", "필수"]) or "yes").strip().lower()
        if raw_id and not rid:
            invalid_ids.append(raw_id.strip())
            continue
        if not rid:
            continue
        all_ids.append(rid)
        if required not in ("no", "false", "n", "optional", "n/a"):
            required_ids.append(rid)
    duplicates = sorted({rid for rid in all_ids if all_ids.count(rid) > 1})
    return {"all": all_ids, "required": required_ids,
            "duplicates": duplicates, "invalid": invalid_ids}


def _acceptance_matrix_ids(content):
    return _acceptance_matrix(content)["required"]


def _acceptance_evidence_rows(content):
    rows = _table_dicts(_section_table_lines(content, ["acceptance evidence", "acceptance evidence review", "수용", "인수"]))
    out = []
    for row in rows:
        raw_id = _first_cell(row, ["id", "acceptance"])
        rid = _acceptance_id(raw_id)
        status = _first_cell(row, ["status", "상태"])
        reason = " ".join(value for value in (
            _first_cell(row, ["reason", "사유"]),
            _first_cell(row, ["evidence", "근거"]),
            _first_cell(row, ["notes", "note", "비고"]),
        ) if value.strip())
        if raw_id or status:
            out.append({"id": rid, "raw_id": raw_id.strip(), "status": status.strip(),
                        "reason": reason.strip(),
                        "raw": row.get("_raw", "")})
    return out


def _has_na_reason(value):
    normalized = re.sub(r"\s+", " ", (value or "").strip()).lower()
    return normalized not in ("", "-", "--", "n/a", "na", "none", "없음", "해당 없음", "해당없음")


def _acceptance_gate(event, profile, snapshot):
    """06 작성 시 04 acceptance evidence와 exact L3 waiver를 검사한다.

    SAGE 의 실패 모드: build/test/review 는 통과했지만 명시 요구사항이 미검증/미구현. 이 gate 는
    04 문서의 구조화된 상태만 확인한다. Waiver는 exact L3 ``NOT TESTED``를 residual WARN으로
    바꿀 뿐 PASS로 만들지 않으며, FAIL/unknown risk/invalid audit에는 적용되지 않는다.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None or not _is_writing_report(event, cfg):
        return None
    verification = profile.get("verification") or {}
    ac = verification.get("acceptance") if isinstance(verification, dict) else None
    if not isinstance(ac, dict) or not ac.get("enabled"):
        return None
    configured_risks = ac.get("require_for_risk")
    required_risks = ({risk for risk in configured_risks if isinstance(risk, str)}
                      if isinstance(configured_risks, list)
                      else {"L2", "L3"})
    # L3 acceptance enforcement is an engine invariant. A profile may opt L1/L2 in or out,
    # but cannot bypass the gate entirely by omitting L3 from require_for_risk.
    required_risks.add("L3")
    cycle_risk = _cycle_risk(event, profile, snapshot, cfg)
    if cycle_risk != "unknown" and cycle_risk not in required_risks:
        return None
    effective_risk = "L3" if cycle_risk == "unknown" else cycle_risk
    if "report_gate_by_risk" in ac:
        by_risk = ac.get("report_gate_by_risk")
        if not isinstance(by_risk, dict):
            mode = "enforce"
        else:
            expected = "enforce" if effective_risk == "L3" else "advisory"
            configured = by_risk.get(effective_risk) or expected
            mode = configured if configured == expected else "enforce"
    elif "report_gate_enforce" in ac:
        legacy_mode = ac.get("report_gate_enforce") or "off"
        # Legacy advisory/off cannot weaken the new L3 invariant. Explicit enforce remains
        # a safe upward-compatible policy for every tier; other legacy values migrate to
        # the fixed L2 advisory/L3 enforce defaults at runtime.
        mode = "enforce" if legacy_mode == "enforce" or effective_risk == "L3" else "advisory"
    else:
        mode = "enforce" if effective_risk == "L3" else "advisory"
    if mode not in ("advisory", "enforce"):
        return None

    configured_statuses = ac.get("statuses")
    statuses = ({status.strip().upper() for status in configured_statuses
                 if isinstance(status, str) and status.strip()}
                if isinstance(configured_statuses, list) else set())
    statuses.update({"PASS", "FAIL", "NOT TESTED", "N/A"})
    configured_unresolved = ac.get("unresolved_statuses")
    unresolved = ({status.strip().upper() for status in configured_unresolved
                   if isinstance(status, str) and status.strip()}
                  if isinstance(configured_unresolved, list) else set())
    # FAIL/NOT TESTED are engine-level unresolved states; validation-bypassed profiles
    # cannot remove either one to turn a required acceptance into PASS.
    unresolved.update({"FAIL", "NOT TESTED"})
    # Profiles cannot mint new resolved states. Only PASS and reasoned N/A resolve;
    # every configured extension remains an unresolved, non-waivable status.
    unresolved.update(statuses - {"PASS", "N/A"})
    phase_docs = snapshot.get("phase_docs") or {}
    docs01 = phase_docs.get("01") or []
    docs04 = phase_docs.get("04") or []
    binding = cycle_binding.resolve(event, snapshot, cfg)

    def fail(detail):
        return {"ok": False, "mode": mode, "detail": detail}

    if binding.get("error"):
        return fail(f"cycle binding 실패: {binding['error']}")
    plan_doc, plan_error = cycle_binding.select_document(docs01, binding["stem"])
    if plan_error:
        return fail(f"01 선택 실패: {plan_error}")
    sel, sel_error = cycle_binding.select_document(docs04, binding["stem"])
    if sel_error:
        return fail(f"04 선택 실패: {sel_error}")
    plan_path = plan_doc.get("path")
    sel_path = sel.get("path")
    matrix = _acceptance_matrix((plan_doc or {}).get("content") or "")
    required_ids = matrix["required"]
    evidence_rows = _acceptance_evidence_rows(sel.get("content") or "")
    if matrix["invalid"]:
        return fail(f"선택된 01 문서({plan_path})에 invalid acceptance ID: {matrix['invalid']}")
    if matrix["duplicates"]:
        return fail(f"선택된 01 문서({plan_path})에 duplicate acceptance ID: {matrix['duplicates']}")
    if not matrix["all"]:
        return fail(f"선택된 01 문서({plan_path or '미선택'})에 acceptance matrix ID 없음")
    if not evidence_rows:
        return fail(f"선택된 04 문서({sel_path})에 acceptance evidence table 없음(PASS/FAIL/NOT TESTED/N/A 필요)")
    known_statuses = set(statuses)
    unresolved_rows = []
    seen_ids = []
    for row in evidence_rows:
        rid = row.get("id") or ""
        raw_id = row.get("raw_id") or ""
        status = (row.get("status") or "").upper()
        if raw_id and not rid:
            unresolved_rows.append({"id": rid, "status": status, "waivable": False,
                                    "detail": f"{row.get('raw')} (acceptance ID 형식 오류: {raw_id!r})"})
        elif not rid:
            unresolved_rows.append({"id": rid, "status": status, "waivable": False,
                                    "detail": f"{row.get('raw')} (acceptance ID 누락)"})
        else:
            seen_ids.append(rid)
        if not status or status not in known_statuses:
            unresolved_rows.append({"id": rid, "status": status, "waivable": False,
                                    "detail": f"{row.get('raw')} (상태값 미인식: {row.get('status')!r})"})
        elif status in unresolved and rid in required_ids:
            unresolved_rows.append({"id": rid, "status": status,
                                    "waivable": status == "NOT TESTED",
                                    "detail": row.get("raw") or f"{rid}: {status}"})
        elif status == "N/A" and not _has_na_reason(row.get("reason")):
            unresolved_rows.append({"id": rid, "status": status, "waivable": False,
                                    "detail": f"{row.get('raw')} (N/A 사유 누락)"})
    duplicate_evidence = sorted({rid for rid in seen_ids if seen_ids.count(rid) > 1})
    if duplicate_evidence:
        return fail(f"04 acceptance evidence duplicate ID: {duplicate_evidence}")
    unknown_ids = sorted(set(seen_ids) - set(matrix["all"]))
    if unknown_ids:
        return fail(f"04 acceptance evidence 에 01 matrix 미정의 ID: {unknown_ids}")
    missing_ids = [rid for rid in required_ids if rid not in set(seen_ids)]
    if missing_ids:
        return fail(f"04 acceptance evidence 에 01 matrix required ID 누락: {missing_ids}")
    if unresolved_rows:
        waiver_cfg = ac.get("waiver") if isinstance(ac.get("waiver"), dict) else {}
        can_consider_waiver = cycle_risk == "L3" and waiver_cfg.get("enabled") is True
        waiver_summary = snapshot.get("acceptance_waivers") or {
            "valid": True, "issues": [], "active": []}
        waiver_uses, remaining = [], []
        for row in unresolved_rows:
            if not (can_consider_waiver and row["waivable"] and row["id"]):
                remaining.append(row)
                continue
            if not waiver_summary.get("valid"):
                issues = "; ".join((waiver_summary.get("issues") or [])[:3]) or "unknown audit error"
                row = dict(row, detail=f"{row['detail']} (waiver audit invalid: {issues})")
                remaining.append(row)
                continue
            matches = [grant for grant in (waiver_summary.get("active") or [])
                       if isinstance(grant, dict)
                       and grant.get("cycle_stem") == binding["stem"]
                       and grant.get("acceptance_id") == row["id"]]
            if len(matches) != 1:
                if len(matches) > 1:
                    row = dict(row, detail=f"{row['detail']} (conflicting exact waivers: {len(matches)})")
                remaining.append(row)
                continue
            grant = matches[0]
            required_grant_fields = ("waiver_id", "reason", "scope", "remaining_evidence", "confirmed_by")
            if any(not isinstance(grant.get(field), str) or not grant.get(field).strip()
                   for field in required_grant_fields):
                remaining.append(dict(row, detail=f"{row['detail']} (malformed exact waiver)"))
                continue
            waiver_uses.append(dict(grant, report_path=sel_path))
        if remaining:
            lines = [row["detail"] for row in remaining]
            preview = "; ".join(lines[:3])
            more = "" if len(lines) <= 3 else f"; ... 외 {len(lines) - 3}건"
            return fail(f"선택된 04 문서({sel_path})에 미해결 acceptance 존재: {preview}{more}")
        if waiver_uses:
            residual = "; ".join(
                f"{grant['acceptance_id']} NOT TESTED, waiver={grant['waiver_id']}, "
                f"reason={grant['reason']}, scope={grant['scope']}, remaining={grant['remaining_evidence']}"
                for grant in waiver_uses)
            return {"ok": False, "mode": "advisory", "waived": True,
                    "detail": f"L3 명시 waiver 적용(상태는 PASS 아님): {residual}",
                    "waiver_uses": waiver_uses}
    return {"ok": True, "mode": mode, "detail": sel_path}


def _audit_gate(event, profile, snapshot):
    """9.5 — report←approve 에 loop_audit 증거 요건을 더한다(advisory-first, run_id 바인딩).

    반환: None(skip) | {"ok": bool, "mode": "advisory"|"enforce", "detail": str}.
    skip 조건: pdca/review_loop 비활성, flag off/미설정, 또는 06 작성이 아님.
    검사: current Cycle-Stem의 05 문서 1개를 exact 선택 → 그 동일 문서에서 APPROVED 마커 + `Loop-Run: <id>` 를
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

    binding = cycle_binding.resolve(event, snapshot, cfg)
    if binding.get("error"):
        return {"ok": False, "mode": mode, "detail": f"cycle binding 실패: {binding['error']}"}

    # current Cycle-Stem의 05 문서 하나만 선택하고 APPROVED와 Loop-Run을 같은 문서에서 읽는다.
    approve_docs = (snapshot.get("phase_docs") or {}).get(approve_phase) or []
    sel, select_error = cycle_binding.select_document(approve_docs, binding["stem"])
    sel_path = (sel or {}).get("path")
    la = snapshot.get("loop_audit") or {}
    has_any = bool(la.get("has_any_records"))

    def fail(detail):
        return {"ok": False, "mode": mode, "detail": detail}

    if select_error:
        return fail(f"05 선택 실패: {select_error}")
    content = sel.get("content") or ""
    marker = (cfg.get("approve_marker") or "APPROVED").upper()
    status, status_error = _final_status(content)
    if status_error or status != marker:
        return fail(f"선택된 05 문서({sel_path}) Final Status 오류: "
                    f"{status_error or f'{status!r} != {marker!r}'}")
    # run_id 는 `review-loop` 가 verbatim 저장(커스텀 --run-id 포함) → 게이트도 비공백 토큰을 그대로 받는다
    # (codex 코드 R1-P1: 협소 charset 이면 rev:123·run/1 같은 합법 run 을 오차단).
    run_ids = []
    for raw in _non_fenced_lines(content):
        match = re.fullmatch(r"Loop-Run:\s*(\S+)", _structured_declaration_line(raw), re.IGNORECASE)
        if match:
            run_ids.append(match.group(1))
    if len(run_ids) != 1:
        hint = "audit 기록 자체가 없음 — 루프 미실행 의심" if not has_any else "05 문서에 Loop-Run 미기재"
        return fail(f"선택된 05 문서({sel_path})의 Loop-Run 선언은 fence 밖에 정확히 1개여야 함"
                    f"(found {len(run_ids)}; {hint})")
    run_id = run_ids[0]
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


def _select_pending_gate_decision(decisions):
    blocked = next((decision for decision in decisions if decision["status"] == "block"), None)
    if blocked:
        return blocked
    warnings = [decision for decision in decisions if decision["status"] == "warn"]
    if not warnings:
        return None
    selected = dict(warnings[0])
    reasons = [decision.get("reason") for decision in warnings if decision.get("reason")]
    selected["reason"] = "; ".join(dict.fromkeys(reasons))
    return selected


def _feedback_gate(event, profile, snapshot):
    """§10-a-C: 미해결 차단성 마커(`!sage-feedback ::`)를 남긴 채 그 파일에 쓰는 것을 막는다.

    규칙은 "마커 있는 파일은 못 고침" 이 아니라 **"고친 뒤에도 마커가 남는가"** 다. 전자로
    만들면 마커를 해소하려는 편집까지 막혀 영원히 못 푸는 자기차단이 된다. 해소하는 방향의
    쓰기(마커를 걷어내는 편집·마커 없는 전체 재작성)는 통과시킨다.

    snapshot["feedback"] 은 어댑터가 주입한다(core 는 순수 — IO 없음). 없으면 skip.
    """
    state = (snapshot or {}).get("feedback")
    if not isinstance(state, dict) or not state.get("enabled"):
        return None
    targets = state.get("targets") or {}
    if not targets:
        return None
    try:
        import feedback_markers
    except Exception:
        return None                     # 모듈 부재 → 판정 불가, 다른 게이트에 맡김

    unresolved = []
    for change in (event.get("changes") or []):
        target = targets.get((change or {}).get("path") or "")
        if not target:
            continue
        if feedback_markers.resolves_blocking(change, target.get("on_disk") or ""):
            continue                    # 해소하는 쓰기 → 통과
        unresolved.append((change.get("path"), target.get("markers") or []))
    if not unresolved:
        return None
    return {"files": [path for path, _ in unresolved],
            "markers": [m for _, markers in unresolved for m in markers]}


_DECLARED_SOURCE = "event"      # cycle_binding 이 env 선언 기원에 붙이는 라벨


def _stamp_cycle_identity(decision: dict, event: dict, profile: dict, snapshot: dict) -> dict:
    """판정에 현재 cycle stem 과 그 출처를 실어 보낸다(판정 자체는 바꾸지 않는다).

    출처를 밖으로 내보내야 하는 이유가 둘이다. 하나는 안내 — stem 을 브랜치 leaf 에서 추론했다면
    올바른 탈출구는 "phase 문서를 작성하라" 가 아니라 "이 사이클이 아니면 선언하라" 다. 다른 하나는
    감사 — env 선언 stem 은 이미 완결된 사이클을 지목해 게이트 전체를 통과시킬 수 있어서, 어댑터가
    그 사실을 기록할 수 있어야 한다. core 는 IO 를 하지 않으므로 여기서는 사실만 싣는다.
    """
    cfg = _pdca_cfg(profile)
    if cfg is None or not isinstance(decision, dict):
        return decision
    binding = cycle_binding.resolve(event, snapshot, cfg)
    source = binding.get("source") or []
    decision["cycle_stem"] = binding.get("stem") or ""
    decision["cycle_source"] = list(source)
    decision["cycle_stem_declared"] = _DECLARED_SOURCE in source
    return decision


def decide(event: dict, profile: dict, snapshot: dict, strategy_result) -> dict:
    """risk-gate 판정. strategy_result: None=미선택 / {found:bool, path?} = 선택된 전략 실행결과."""
    return _stamp_cycle_identity(
        _decide(event, profile, snapshot, strategy_result), event, profile, snapshot)


def _decide(event: dict, profile: dict, snapshot: dict, strategy_result) -> dict:
    c = classify_risk(event, profile)
    risk = c["risk"]

    if risk == "DESKTOP_BLOCK":
        return {"status": "block", "exit_code": 2, "risk": "DESKTOP",
                "message_key": "block_desktop", "reason": c["reason"], "file_short": c["file_short"]}

    # §10-a-C 개발자 피드백 마커: 미해결 차단성 마커를 남긴 채 그 파일에 쓰면 차단.
    # 위험도와 무관하게 적용한다 — "묵은 의문 위에 새 구현을 쌓지 마라" 는 L1 이든 L3 이든 같다.
    fg = _feedback_gate(event, profile, snapshot)
    if fg is not None:
        detail = "; ".join(f"{m['path']}:{m['line']} {m['text']}" for m in fg["markers"][:3])
        return {"status": "block", "exit_code": 2, "risk": "FEEDBACK",
                "message_key": "block_feedback_unresolved",
                "reason": f"미해결 차단성 마커 {len(fg['markers'])}건 — {detail}",
                "file_short": ", ".join(fg["files"][:3])}

    # PDCA cycle identity is a prerequisite for governed source changes and every phase write.
    # Do not infer from branch numbers or recent mtimes: zero/multiple/conflicting candidates block.
    cfg = _pdca_cfg(profile)
    if cfg is not None and (_is_phase_write(event, cfg) or risk in ("L1", "L2", "L3")):
        binding = cycle_binding.resolve(event, snapshot, cfg)
        if binding.get("error"):
            return {"status": "block", "exit_code": 2, "risk": "PDCA",
                    "message_key": "block_cycle_binding",
                    "reason": f"cycle binding 실패: {binding['error']}",
                    "file_short": c["file_short"]}
        changed_phases = _changed_phase_ids(event, cfg)
        report_phase = str(cfg.get("report_phase") or "")
        dependency_phases = {str(phase.get("id") or "") for phase in (cfg.get("phases") or [])}
        dependency_phases.discard(report_phase)
        dependency_phases.discard("")
        mixed = sorted(changed_phases & dependency_phases)
        if report_phase and report_phase in changed_phases and mixed:
            return {"status": "block", "exit_code": 2, "risk": "PDCA",
                    "message_key": "block_report_mixed_evidence",
                    "reason": (f"report phase {report_phase}와 dependency phase {mixed}를 같은 변경에서 "
                               "수정하면 pre-write snapshot으로 검증할 수 없음"),
                    "file_short": c["file_short"]}

    # PDCA report←approve 게이트: report phase 문서 작성은 L0(plan_docs)이라 아래 단축 전에 검사.
    # (pdca 비활성이거나 report/approve 미설정 → None → skip, 하위호환)
    rg = _report_gate(event, profile, snapshot)
    if rg is not None and not rg["approved"]:
        return {"status": "block", "exit_code": 2, "risk": "PDCA",
                "message_key": "block_report_without_approval",
                "reason": (f"{rg['report_phase']} 작성 전 {rg['approve_phase']} 승인(APPROVED) 필요: "
                           f"{rg.get('detail') or 'same-cycle document unavailable'}"),
                "file_short": c["file_short"]}

    # Acceptance evidence gate: 04 가 요구사항별 PASS/FAIL/NOT TESTED 를 기록했는지 확인.
    # build/test/lint 통과가 사용자 요구사항 충족을 자동 증명하지 않는 갭을 advisory-first 로 닫는다.
    pending_gate_decisions = []
    acg = _acceptance_gate(event, profile, snapshot)
    if acg is not None and not acg["ok"]:
        if acg.get("waived"):
            pending_gate_decisions.append({"status": "warn", "exit_code": 0, "risk": "PDCA",
                                           "message_key": "warn_report_with_l3_waiver",
                                           "reason": acg["detail"],
                                           "waiver_uses": acg.get("waiver_uses") or [],
                                           "file_short": c["file_short"]})
        elif acg["mode"] == "enforce":
            pending_gate_decisions.append({"status": "block", "exit_code": 2, "risk": "PDCA",
                                           "message_key": "block_report_without_acceptance",
                                           "reason": f"acceptance evidence 미충족(enforce): {acg['detail']}",
                                           "file_short": c["file_short"]})
        else:
            pending_gate_decisions.append({"status": "warn", "exit_code": 0, "risk": "PDCA",
                                           "message_key": "warn_report_without_acceptance",
                                           "reason": f"acceptance evidence 미충족(advisory): {acg['detail']}",
                                           "file_short": c["file_short"]})

    # 9.5 report←approve audit 증거(F-5): 마커는 있으나 cycle 05 가 가리키는 loop run 이 closed+APPROVED 가
    # 아니면 advisory=WARN / enforce=BLOCK. review_loop 비활성·flag off 면 ag=None → skip(하위호환).
    ag = _audit_gate(event, profile, snapshot)
    if ag is not None and not ag["ok"]:
        if ag["mode"] == "enforce":
            pending_gate_decisions.append({"status": "block", "exit_code": 2, "risk": "PDCA",
                                           "message_key": "block_report_without_audit",
                                           "reason": f"리뷰 루프 audit 증거 미충족(enforce): {ag['detail']}",
                                           "file_short": c["file_short"]})
        else:
            pending_gate_decisions.append({"status": "warn", "exit_code": 0, "risk": "PDCA",
                                           "message_key": "warn_report_without_audit",
                                           "reason": f"리뷰 루프 audit 증거 미충족(advisory): {ag['detail']}",
                                           "file_short": c["file_short"]})

    selected = _select_pending_gate_decision(pending_gate_decisions)
    if selected:
        return selected

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

    plan_exists = _bound_plan_exists(event, profile, snapshot)

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
