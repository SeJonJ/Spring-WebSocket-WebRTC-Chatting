"""io_claude — pre-implementation-gate 의 Claude 전용 IO (입력추출/declared/렌더). R1 분리.

런타임이 진짜 다른 부분만: Write/Edit/MultiEdit 입력추출, .claude/logs declared 읽기,
stdout 평문 렌더(채널). 본문 로직(snapshot/전략/decide)은 hook_runtime 공유,
사용자 문구는 messages 모듈 공유(5-3 — io_codex 와의 테이블 중복 제거).
"""
import json
import os
import re

import messages

RUNTIME = "claude"
HOST_DIR = ".claude"
ROOT_ENV = "CLAUDE_PROJECT_DIR"


def should_skip(raw):
    return False   # claude: 모든 Write/Edit/MultiEdit 대상


def extract_changes(raw, rel):
    ti = raw.get("tool_input") or {}
    fp = ti.get("file_path") or ""
    blob = (ti.get("content") or "") or (ti.get("new_string") or "")
    for e in (ti.get("edits") or []):
        blob += "\n" + (e.get("new_string") or "")
    return [{"path": rel(fp), "op": "write", "content": blob}] if fp else []


def read_declared_level(raw, root):
    sid = re.sub(r"[^A-Za-z0-9_-]", "_", raw.get("session_id", "") or "nosession")[:64]
    dp = os.path.join(root, HOST_DIR, "logs", f"declared-risk-{sid}.json")
    try:
        with open(dp, encoding="utf-8") as f:
            return json.load(f).get("level")
    except Exception:
        return None


def render_gate(decision, profile):
    # 문구는 messages 공유(SSOT), 채널은 Claude=stdout 평문.
    m = messages.gate_text(decision, profile, RUNTIME)
    if m:
        print(m)
    return decision["exit_code"]


def render_declared_capture(level):
    # Claude 출력 프로토콜: plain text (stdout = additionalContext)
    print(messages.declared_capture_text(level, RUNTIME))


# --- post-tool-logger IO (Claude: tool_input.file_path 단일) ---
def logger_tool_name(raw):
    return raw.get("tool_name", "") or ""


def extract_logged_changes(raw, rel):
    fp = (raw.get("tool_input") or {}).get("file_path") or ""
    return [{"path": rel(fp), "op": "write"}] if fp else []


# --- pre-phase4-checklist-gate IO (Claude) ---
def extract_phase4_changes(raw, rel):
    fp = (raw.get("tool_input") or {}).get("file_path") or ""
    return [{"path": rel(fp), "op": "write"}] if fp else []


def render_phase4(decision):
    dec = decision
    s = dec["status"]
    if s == "block":
        lines = [messages.phase4_block_header(dec['total_unchecked'], dec['base'], RUNTIME),
                 "  04-analyze 작성 전 아래 항목을 완료(또는 N/A 사유와 함께 [x])하세요:"]
        for ev in dec["evidence"]:
            lines.append(f"  ▸ {ev['label']}: {ev['file']} ({len(ev['unchecked'])}건 미완료)")
            for it in ev["unchecked"][:6]:
                t = it["text"]
                lines.append(f"      L{it['line']}: {t if len(t) <= 90 else t[:87] + '...'}")
            extra = len(ev["unchecked"]) - 6
            if extra > 0:
                lines.append(f"      ... 외 {extra}건")
        msg = "\n".join(lines)
    elif s == "warn":
        msg = messages.phase4_warn(dec['base'], RUNTIME)
    elif s == "ok":
        msg = messages.phase4_ok(dec['base'], RUNTIME)
    else:
        msg = ""
    if msg:
        print(msg)
    return dec["exit_code"]


# --- stop-compliance-report IO (Claude) ---
def attach_policy_results(model, profile, entries, raw_text, kc_result):
    # F7: claude 도 knowledge_capture 주입. output_contract 는 미적용(Codex-only 설계 + 마커 비독립).
    model["sections"]["policy_results"].append(kc_result)


def render_stop_result(today, block_reason=None):
    print(messages.report_saved_text(HOST_DIR, today, RUNTIME))
    if block_reason:
        print(f"[stop-compliance-report] ❌ {block_reason}")
        return 2
    return 0
