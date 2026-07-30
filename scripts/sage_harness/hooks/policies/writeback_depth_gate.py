"""writeback_depth_gate — Stop 훅 정책: L2/L3 사이클의 write-back 심층 노트가 실제로
host depth self-review 를 거쳤는지 06 자기선언으로 사후 확인.

배경: sage-team write-back 은 L2/L3 노트를 vault 손저작 깊이의 심층 골격으로 쓰도록
지시하지만, 그 지침도 self-review(작성 후 각 섹션이 실내용인지 재확인)도 host 자율이다.
CLI 구조검사는 마커 '존재'만 보고 깊이는 못 본다(hollow 섹션을 통과 — false-assurance 회피
설계). 지침을 무시하고 얕은 노트를 써도 아무것도 막지 않아, 첫 실전 L2 에서 얕은 노트가
그대로 통과했다.

이 게이트는 품질을 판정하지 않는다 — self-review 라는 사람판단 단계가 *실제로 돌았다는
증거*를 요구한다. 06 은 self-review 후 헤더 메타블록에 `Depth-Self-Review: performed`
(의도적 얕은 노트는 L1 로 재분류 후 `skipped`)를 자기선언하고, 게이트는 06 만 읽어 그
선언을 확인한다(품질은 skill 지침·host self-review 소관 그대로).

범위/제약은 retro_gate 와 동일: Stop 훅은 stop_hook_active 때문에 세션당 정확히 1회만
block 가능하다(플랫폼 제약). 그래서 enforce 는 '완료 전 종료 불가'가 아니라 '1회 강넛지 +
사후기록'이다. 미완료로 무시하고 종료하면 세션은 끝나지만, 그 Stop 이 쓰는
compliance-<날짜>.md 에 WARN/BLOCK 으로 남아 사후 확인할 수 있다.
"""

_SEVERITIES = ("INFO", "OK", "WARN", "BLOCK")


def _unchecked_severity(mode, stop_hook_active):
    """게이트 활성 + 미선언 시 severity. enforce 첫 Stop 만 BLOCK, 그 외(advisory·재시도) WARN.
    enforce 라도 stop_hook_active=true(이미 이번 세션 1회 block 함)면 플랫폼상 재차단 불가 →
    WARN 으로 낮춘다(무한 Stop 재호출 방지). advisory 는 애초에 block 안 함."""
    return "BLOCK" if (mode == "enforce" and not stop_hook_active) else "WARN"


def check(mode, applies, declared, stop_hook_active, vault_enabled=True):
    """순수 함수. 입력은 전부 adapter(hook_runtime.py)가 세션/파일시스템에서 미리 계산해 넘긴다.

    mode: "off"|"advisory"|"enforce"|기타(무효 → off 취급).
    applies: 이번 세션에 심층 노트 대상 06(L2/L3, 또는 Risk Level 미기재=보수적 L2)이 쓰였는가.
             L1 06·06 없음 → False(L1 은 얕은 노트가 정상이라 게이트 대상 아님).
    declared: applies 대상 06 이 전부 `Depth-Self-Review: performed` 를 자기선언했는가.
    stop_hook_active: 이번 Stop 이 이전 Stop 훅 block 때문에 생긴 재시도인가(플랫폼 제공 필드).
    vault_enabled: knowledge_capture write-back(update_after_dev + usable vault)이 켜져 있는가 —
                   꺼지면 심층 노트 자체가 안 만들어져 통과 불가능한 걸 강제하게 되므로 skip.

    반환: {"name": "writeback_depth_gate", "severity": one of _SEVERITIES, "text": str}.
    severity="BLOCK" 일 때만 오케스트레이터가 프로세스를 exit 2(codex: decision:block)로 종료한다.
    """
    if mode not in ("advisory", "enforce"):
        return {"name": "writeback_depth_gate", "severity": "INFO",
                "text": "N/A — pdca.writeback.depth_review_gate=off"}
    if not vault_enabled:
        return {"name": "writeback_depth_gate", "severity": "INFO",
                "text": "N/A — knowledge_capture write-back off (심층 노트 미생성 → 게이트 무동작)"}
    if not applies:
        return {"name": "writeback_depth_gate", "severity": "INFO",
                "text": "N/A — 이번 세션에 L2/L3 심층 노트 대상 06 작성 없음"}
    if declared:
        return {"name": "writeback_depth_gate", "severity": "OK",
                "text": "depth self-review 자기선언 확인됨 (06: Depth-Self-Review: performed)"}

    text = ("L2/L3 06 작성됐으나 depth self-review 자기선언 없음 — write-back 노트의 각 섹션이 "
            "빈 헤더가 아닌 실내용(변경 내역의 파일:함수:line, 검증의 구체 결과 등)인지 재확인한 뒤 "
            "06 헤더에 `Depth-Self-Review: performed` 를 기록하세요. 의도적 얕은 노트면 00 Risk Level 을 "
            "L1 로 재분류하고 `Depth-Self-Review: skipped` 로 선언하세요.")
    return {"name": "writeback_depth_gate", "severity": _unchecked_severity(mode, stop_hook_active), "text": text}
