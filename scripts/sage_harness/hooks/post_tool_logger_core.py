"""post-tool-logger — canonical core (pure policy, IO 없음, 도메인 기본값 0).

계약: decide(event, profile) -> decision  (런타임 중립, 결정론적).
- event: adapter 가 런타임 raw 입력을 정규화한 표준 이벤트(+ branch, + now_utc).
- profile: 프로젝트 선언값(외부 주입 필수). core 에 도메인 기본값을 두지 않는다.

양 런타임(claude/codex) hook 공유 알고리즘
(tracked 파일 type 분류 후 JSONL 로그 엔트리 생성).
- structural_io_adapter: 입력추출(Claude file_path 단일 vs Codex apply_patch 본문 다중) → adapter 가 changes[] 로 정규화
- profile_bound: file_type_map(경로글롭→type) 은 프로젝트 선언값 → profile
- algorithm canonical: skip_untyped (미분류 미기록). Claude 의 type=other 기록은 회귀로 보고 unresolved.
"""

import fnmatch

CONTRACT_VERSION = "1"


def _classify(short_path: str, file_type_map: list) -> str | None:
    """ordered file_type_map 에서 첫 매치 type 반환 (없으면 None)."""
    for entry in file_type_map:
        glob = entry.get("glob", "")
        if glob and fnmatch.fnmatch(short_path, glob):
            return entry.get("type")
    return None


def decide(event: dict, profile: dict) -> dict:
    """tool 변경(changes[])을 profile 로 분류해 JSONL 로그 엔트리를 생성할지 결정한다.

    event:   { tool, session_id, branch, now_utc, changes:[{path(rel), op}] }
    profile: { file_type_map:[{glob,type}](첫매치), skip_untyped, log_schema_version }
    decision:{ kind, action(log|noop), log_file, log_entries:[{ts,tool,file,type,branch,session}], exit_code }
    """
    changes = event.get("changes") or []
    tool = event.get("tool") or ""
    branch = event.get("branch") or "unknown"
    session = event.get("session_id") or ""
    now_utc = event.get("now_utc") or ""
    today = now_utc[:10]  # "YYYY-MM-DDT..." → "YYYY-MM-DD"

    file_type_map = profile.get("file_type_map") or []
    skip_untyped = profile.get("skip_untyped", True)

    entries = []
    for ch in changes:
        short = ch.get("path") or ""
        if not short:
            continue
        typ = _classify(short, file_type_map)
        if typ is None:
            if skip_untyped:
                continue
            typ = "other"
        entries.append({
            "ts": now_utc,
            "tool": tool,
            "file": short,
            "type": typ,
            "branch": branch,
            "session": session,
        })

    return {
        "kind": "post_tool_log",
        "action": "log" if entries else "noop",
        "log_file": f"session-{today}.jsonl",
        "log_entries": entries,
        "exit_code": 0,
    }
