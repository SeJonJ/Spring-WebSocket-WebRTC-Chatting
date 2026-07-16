"""stop-compliance 확장 정책 — output_contract_check (보존, Codex-only policy_delta).

원본 .codex/hooks/stop-compliance-report.sh 의 Output Contract 검사를 충실 이식:
transcript 마지막 assistant 텍스트에서 5개 핵심 섹션 마커를 세어 hit>=4 → OK / else WARN.

⚠️ Codex runtime 결합(transcript_path 의존). canonical CORE 미병합(promote 보류, manifest.unresolved).
   Codex adapter 만 이 정책을 policy_results 에 주입(claude adapter 는 미적용 — Claude 엔 대응 검사 없음).
"""

CONTRACT_VERSION = "1"

# EH-2(제약#2 독립성): 기본 마커는 **중립**(스택/빌드툴 토큰 0). 이전엔 Impact 에 backend/frontend/desktop,
# Validation 에 gradlew 가 하드코딩돼 비-웹 인스턴스에서 부정확했다. 프로젝트 고유 토큰은
# profile.output_contract.markers 로 주입(예: 웹앱이 Impact 에 backend/frontend 추가). hit>=4 → OK.
_DEFAULT_MARKERS = {
    "Task Summary / 요약": ["task summary", "작업 요약", "요약"],
    "Risk Level": ["risk level", "risk", "위험", "l0", "l1", "l2", "l3"],
    "Impact": ["impact", "영향"],
    "Modified Files": ["modified files", "변경 파일", "수정 파일", "변경된 파일"],
    "Validation": ["validation", "검증", "build", "test"],
}


def check(last_assistant_text, has_code_changes: bool, markers=None) -> dict:
    """markers(profile.output_contract.markers, {섹션:[토큰]}) 주입 시 사용, 없으면 중립 기본값."""
    if not has_code_changes:
        return {"name": "output_contract", "severity": "INFO", "text": "N/A — 코드 변경 없음 (적용 대상 아님)"}
    if not last_assistant_text:
        return {"name": "output_contract", "severity": "INFO", "text": "N/A — transcript 접근 불가 또는 추출 실패"}
    mk = markers if isinstance(markers, dict) and markers else _DEFAULT_MARKERS
    lt = last_assistant_text.lower()
    present = {k: any(str(t).lower() in lt for t in v) for k, v in mk.items()}
    missing = [k for k, ok in present.items() if not ok]
    total = len(present)
    hit = total - len(missing)
    threshold = max(1, total - 1)   # "최대 1개 누락 허용"(기본 5→4) — 마커 수와 무관하게 일반화
    if hit >= threshold:
        return {"name": "output_contract", "severity": "OK", "text": f"output contract 핵심 섹션 {hit}/{total} 충족"}
    return {"name": "output_contract", "severity": "WARN",
            "text": f"output contract 섹션 {hit}/{total} 만 감지 (누락 추정: {', '.join(missing)}) → docs/agent/output-contract.md 형식 권장"}
