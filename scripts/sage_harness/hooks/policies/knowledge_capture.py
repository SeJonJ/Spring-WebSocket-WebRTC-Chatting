"""stop-compliance 확장 정책 — knowledge_capture (보존, OPTION-gated policy_delta).

원본 .codex/hooks/stop-compliance-report.sh 의 Wiki Knowledge Capture 검사를 충실 이식:
코드 변경 세션이면 vault wiki/log.md 의 mtime 이 가장 이른 코드변경 ts 이후인지 확인 → 캡처 추정.

⚠️ OPTION(knowledge_capture, provider=obsidian). vault_path 비면 N/A. canonical CORE 미병합.
   IO(파일 mtime)는 adapter 가 gather → 이 모듈은 숫자 비교만(순수, 테스트 용이).
"""

CONTRACT_VERSION = "1"


def check(vault_root: str, has_code_changes: bool, wiki_log_mtime, earliest_code_ts) -> dict:
    """wiki_log_mtime: vault wiki/log.md 의 mtime(없으면 None). earliest_code_ts: 가장 이른 코드변경 epoch(없으면 None)."""
    if not has_code_changes:
        return {"name": "knowledge_capture", "severity": "INFO", "text": "N/A — 코드 변경 없음 (vault 캡처 대상 아님)"}
    if not vault_root:
        return {"name": "knowledge_capture", "severity": "INFO", "text": "N/A — vault_path 미설정 (OPTION off)"}
    if wiki_log_mtime is None:
        return {"name": "knowledge_capture", "severity": "WARN", "text": "vault wiki/log.md 없음 — 지식 캡처 상태 확인 불가"}
    if earliest_code_ts is None:
        return {"name": "knowledge_capture", "severity": "INFO", "text": "N/A — 코드 변경 시각 파싱 불가"}
    if wiki_log_mtime >= earliest_code_ts:
        return {"name": "knowledge_capture", "severity": "OK", "text": "코드 변경 이후 vault wiki/log.md 갱신됨 (캡처 추정 완료)"}
    return {"name": "knowledge_capture", "severity": "WARN",
            "text": "코드 변경 후 vault wiki/log.md 미갱신 — 지식 캡처 누락 가능 (BUG/TECH/SPEC/POSTMORTEM 시 노트 작성)"}
