"""messages — 게이트/컴플라이언스 hook 사용자 메시지 SSOT (5-3).

io_claude/io_codex 가 각자 들고 있던 message_key→문구 테이블을 여기로 합친다.
런타임 차이(emoji vs ASCII, 대시 —/-, 구분자 개행/파이프, 스킬 접두 //$, phase 화살표
→/->) 는 runtime 인자로 분기하고, io_* 는 채널(stdout / stderr / hookSpecific JSON)과
exit code 만 담당한다. 문구는 정보량이 많은 쪽으로 통일 — codex 도 동일 본문·힌트를 받는다
(4차 잔여였던 두 테이블 드리프트 제거, 의도된 출력 변경).
"""

_EMOJI = {"BLOCK": "⛔", "WARN": "⚠️", "OK": "✅"}


def _dash(runtime):
    return " - " if runtime == "codex" else " — "


def _review_cmd(runtime):
    # 스킬 호출 접두는 런타임 규약: codex=$, claude=/. 이건 드리프트가 아니라 정당한 치환.
    return "$sage-review" if runtime == "codex" else "/sage-review"


def desktop_hint(profile):
    return (profile.get("risk") or {}).get("desktop_block_hint", "원본 경로 수정 후 동기화")


def _gate_record(decision, profile):
    """message_key → (sev, scope, text, show_reason, hint). 동적 필드(fs/rs/risk/miss)는
    여기서 채운다. hint 의 {rv} 는 렌더 시 런타임별 sage-review 호출로 치환된다."""
    rs = decision.get("reason", "")
    risk = decision.get("risk", "")
    miss = ", ".join(decision.get("missing_phases") or [])
    return {
        "block_desktop": ("BLOCK", "", "동기화 산출물/금지 경로 직접수정 금지.", False, desktop_hint(profile)),
        "block_l3_no_plan": ("BLOCK", "L3", "L3 작업 + plan 문서 없음.", True,
                             "plan 문서 생성 + L3 리뷰 프로토콜(2라운드) 수행"),
        "block_l3_strategy_unresolved": ("BLOCK", "L3", "L3 review 매칭 전략 미선택(unresolved) → 리뷰 확인 불가.", True,
                             "(override required: SAGE manifest 에서 find_l3_review 전략 canonical 선택 필요)"),
        "warn_l3_no_review": ("WARN", "L3", "2라운드 리뷰 문서 미확인.", True, None),
        "warn_l2_no_plan": ("WARN", "L2", "소스/설정 변경인데 plan 문서 없음.", True, None),
        "warn_l0_l3_content": ("WARN", "L0", "문서/plan 에 L3 내용 키워드 감지 — 민감정보 노출 점검.", False, None),
        "block_phase_incomplete": ("BLOCK", risk, f"의무 PDCA phase 미작성: [{miss}].", True,
                             "해당 phase 문서를 먼저 작성하세요 (docs/agent/pdca-templates.md)"),
        "warn_phase_incomplete": ("WARN", "L1", f"권장 PDCA phase 미작성: [{miss}].", False, None),
        "block_report_without_approval": ("BLOCK", "PDCA", f"{rs}.", False,
                             "approve phase 문서에 APPROVED 기록 후 report 작성"),
        "block_report_without_audit": ("BLOCK", "PDCA", f"{rs}.", False,
                             "Phase 05 를 {rv} 로 돌려 loop 을 닫고(APPROVED) 05 문서에 'Loop-Run: <run_id>' 를 기록하세요"),
        "warn_report_without_audit": ("WARN", "PDCA", f"{rs}.", False,
                             "(advisory) Phase 05 리뷰 루프 audit 증거 권장 — {rv} 로 loop 실행 + 05 에 'Loop-Run: <run_id>' 기록"),
        "block_report_without_acceptance": ("BLOCK", "PDCA", f"{rs}.", False,
                             "04-analyze 에 acceptance evidence(PASS/FAIL/NOT TESTED/N/A)를 기록하고 05 를 다시 검토하세요"),
        "warn_report_without_acceptance": ("WARN", "PDCA", f"{rs}.", False,
                             "(advisory) 04-analyze 의 acceptance evidence 를 보강하세요"),
        "ok_l3": ("OK", "L3", "review 확인됨", False, None),
        "ok_l2": ("OK", "L2", "plan 확인", False, None),
    }.get(decision.get("message_key"))


def gate_text(decision, profile, runtime):
    """게이트 결정 → 런타임별 렌더 문자열(매칭 없으면 ''). 채널/exit 은 io_* 가 처리."""
    rec = _gate_record(decision, profile)
    if not rec:
        return ""
    sev, scope, text, show_reason, hint = rec
    fs = decision.get("file_short", "")
    rs = decision.get("reason", "")
    tag = f"[GATE {sev}{_dash(runtime)}{scope}]" if scope else f"[GATE {sev}]"
    prefix = "" if runtime == "codex" else f"{_EMOJI[sev]} "
    if sev == "OK":
        line = f"{prefix}{tag} {text} | {fs}"
    else:
        line = f"{prefix}{tag} {text} 파일: {fs}"
        if show_reason and rs:
            line += f" | 근거: {rs}"
    if hint:
        hint = hint.replace("{rv}", _review_cmd(runtime))
        line += (" | " if runtime == "codex" else "\n  → ") + hint
    return line


def declared_capture_text(level, runtime):
    core = f"[Risk 선언 포착] 이번 세션 작업 레벨: {level} — 소스 수정 시 해당 레벨 게이트가 적용됩니다."
    return core if runtime == "codex" else f"ℹ️  {core}"


def report_saved_text(host_dir, today, runtime):
    core = f"Compliance report saved: {host_dir}/logs/compliance-{today}.md"
    return core if runtime == "codex" else f"📋 {core}"


# --- pre-phase4-checklist-gate 공유 문구 ---
# (block 의 evidence 리스트 본문은 런타임별 구조라 io_* 가 조립; 여기선 한 줄 문구만 통일)
def _phase4_arrow(runtime):
    return "3->4" if runtime == "codex" else "3→4"


def phase4_block_header(total_unchecked, base, runtime):
    prefix = "" if runtime == "codex" else "⛔ "
    return (f"{prefix}[GATE BLOCK{_dash(runtime)}Phase {_phase4_arrow(runtime)}] "
            f"체크리스트 미완료 {total_unchecked}건 (기능: {base})")


def phase4_warn(base, runtime):
    prefix = "" if runtime == "codex" else "⚠️  "
    return (f"{prefix}[GATE WARN{_dash(runtime)}Phase {_phase4_arrow(runtime)}] "
            f"'{base}' 의 03-implementation 문서를 찾지 못했습니다.")


def phase4_ok(base, runtime):
    prefix = "" if runtime == "codex" else "✅ "
    return (f"{prefix}[GATE OK{_dash(runtime)}Phase {_phase4_arrow(runtime)}] "
            f"'{base}' 체크리스트 완료 확인")
