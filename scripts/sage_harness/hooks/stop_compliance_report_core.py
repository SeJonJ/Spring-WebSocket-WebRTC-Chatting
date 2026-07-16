"""stop-compliance-report — canonical core (pure, 부분추출).

양 런타임 실측 기반 SAGE stop hook 설계(Codex 2R 합의).
공유 core 만 canonical: JSONL 집계 → activity_summary → gate compliance 3종 → report_model → markdown.

⚠️ policy_delta(병합금지, Codex-only/OPTION — 별도 정책모듈 보존):
- output_contract_check: transcript 결합 → Codex-only (CORE 승격 보류, unresolved)
- knowledge_capture: obsidian OPTION (vault_path 비면 N/A)

계약: decide(event, profile, snapshot) -> report_model / render_markdown(report_model) -> str. (둘 다 pure)
snapshot = { entries[], today, branch, runtime }. L3 패턴 단일소스 = profile.risk.l3_filename_globs.
"""

from collections import defaultdict

CONTRACT_VERSION = "1"


def _l3_tokens(profile: dict) -> list:
    """profile.risk.l3_filename_globs('*high-risk*' 등) → substring 토큰. 단일소스 재사용."""
    out = []
    for g in (profile.get("risk", {}) or {}).get("l3_filename_globs", []):
        t = g.strip("*").lower()
        if t:
            out.append(t)
    return out


def decide(event: dict, profile: dict, snapshot: dict) -> dict:
    entries = snapshot.get("entries") or []
    today = snapshot.get("today", "")
    branch = snapshot.get("branch") or "unknown"

    by_type = defaultdict(list)
    for e in entries:
        by_type[e.get("type", "other")].append(e.get("file", ""))

    # 제약 #2(독립): file type 체계는 profile.compliance 주입. 없으면 raw type 별 generic 그룹(도메인 무관).
    comp = profile.get("compliance", {}) or {}
    groups_cfg = comp.get("activity_groups")
    if not groups_cfg:
        groups_cfg = [{"label": t, "types": [t]} for t in sorted(by_type) if t != "other"]
    plan_types = comp.get("plan_types", [])
    plan_gate_code_types = comp.get("plan_gate_code_types", [])
    reminder = comp.get("convention_reminder")  # {types:[...], text:"..."} 선택

    def files_of(types):
        out = set()
        for t in types:
            out |= set(by_type.get(t, []))
        return sorted(out)

    activity = [{"label": g["label"], "count": len(files_of(g["types"])), "files": files_of(g["types"])}
                for g in groups_cfg]

    all_code_files = files_of([t for g in groups_cfg for t in g["types"]])
    l3_tokens = _l3_tokens(profile)
    l3_files = sorted({f for f in all_code_files if any(t in f.lower() for t in l3_tokens)})

    plan_present = bool(files_of(plan_types))
    code_present = bool(files_of(plan_gate_code_types))

    issues = []
    if code_present and not plan_present:
        issues.append({"severity": "WARN", "key": "code_without_plan",
                       "text": comp.get("plan_gate_text", "코드 변경이 있었으나 plan 문서 활동 없음 (L2 gate 참조)")})
    if l3_files:
        issues.append({"severity": "NOTICE", "key": "l3_pattern_detected",
                       "text": f"L3 패턴 파일 수정 감지: {', '.join(l3_files)} → L3 리뷰 프로토콜(2라운드) 확인 필요"})
    if reminder and files_of(reminder.get("types", [])):
        issues.append({"severity": "INFO", "key": "convention_reminder",
                       "text": reminder.get("text", "변경 컨벤션 검증 확인 권장")})

    modified = sorted({e.get("file", "") for e in entries if e.get("file")})

    return {
        "kind": "stop_compliance",
        "sections": {
            "header": {"date": today, "branch": branch, "total_tool_calls": len(entries)},
            "activity_summary": activity,   # [{label, count, files}] — profile 그룹(또는 raw type generic)
            "gate_compliance": {"issues": issues},
            "modified_files": modified,
            "policy_results": [],  # 확장 슬롯 — output_contract/knowledge_capture 등 OPTION/Codex policy 가 붙임 (core 미해석)
        },
        "exit_code": 0,
    }


def render_markdown(report_model: dict) -> str:
    s = report_model["sections"]
    h = s["header"]
    a = s["activity_summary"]   # [{label, count, files}]
    lines = [
        f"# Compliance Report — {h['date']}",
        f"Branch: {h['branch']}  |  Total tool calls logged: {h['total_tool_calls']}",
        "",
        "## Activity Summary",
        "| 구분 | 파일 수 |", "|---|---|",
    ]
    for g in a:
        lines.append(f"| {g['label']} | {g['count']} |")
    lines += ["", "## Gate Compliance"]
    issues = s["gate_compliance"]["issues"]
    if not issues:
        lines.append("✅ 감지된 위반 없음")
    else:
        for it in issues:
            lines.append(f"[{it['severity']}] {it['text']}")
    lines += ["", "## Modified Files"]
    for f in s["modified_files"]:
        lines.append(f"- {f}")
    # policy_results (OPTION/Codex 확장이 붙인 경우만)
    if s.get("policy_results"):
        lines += ["", "## Policy Results"]
        for pr in s["policy_results"]:
            lines.append(f"[{pr.get('severity','INFO')}] {pr.get('name','')}: {pr.get('text','')}")
    return "\n".join(lines) + "\n"
