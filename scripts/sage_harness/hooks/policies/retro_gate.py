"""retro_gate — Stop 훅 정책: `sage retro --check` 가 실제로 통과했는지 사후 확인(9-C v1).

배경: `sage retro --check` 는 host 가 스스로 실행해야만 효력이 있다. 06←05 훅으로는 강제할 수 없다
(sage-team 절차상 06 이 retro 보다 먼저 쓰여, 06 게이트가 도는 시점엔 retro 노트가 아직 없다). 유일하게
06 과 retro 둘 다를 볼 수 있는 지점이 세션 종료(Stop) 다.

**범위(v1, 의도적으로 좁음)**: Stop 훅의 `stop_hook_active` 를 지키면(Claude Code·codex 공식 문서 확인)
block 은 세션당 정확히 1회만 가능하다 — 이건 설계 선택이 아니라 플랫폼 제약. 그래서 이 게이트의
"enforce" 는 "완료할 때까지 못 끝냄" 이 아니라 **"1회 강한 넛지 + 감사기록"** 이다. 무시하고 재시도하면
세션은 끝나지만, retro_audit 에 "미완료로 종료됨" 이 남아 이후 `sage doctor`/다음 사이클이 볼 수 있다.
진짜 차단(완료 전 세션 종료 불가)은 별도 백로그(9-C-2, 새 결정론 게이트 필요 — Stop 훅만으론 불가능).

**결속(binding)**: 06 은 이번 세션에 쓰인 것만 인정하고, 대응 retro run 은 **06 문서가 자기선언한**
`Loop-Run: <run_id>` 로 특정한다(05 를 stem 으로 추측하지 않는다 — codex W1: 전역 stem 스캔은 다중 06 을
한 집합으로 가리거나 과거 동명 05 를 오결속). run_id 는 sage-review 가 05 에 기록하고 06 작성 시 06 으로
복사된다(재개 가능 PDCA: 05 는 이전 세션, 06 은 이번 세션이 정상 — 외부 보완 피드백 Item 2). 06 이
이번 세션에 쓰였는데 자기선언 run 을 유일하게 특정 못 하면(마커 없음=no_candidate, 한 06 에 마커 여럿
=ambiguous) 조용히 skip 하지 않고 결속 불가로 WARN(advisory)/BLOCK(enforce) 한다 — 조용한 skip 은 게이트
우회이기 때문. 다중 06 은 어댑터가 06 별 결속을 본 뒤 worst-case 로 축약해 넘긴다.
"""

_SEVERITIES = ("INFO", "OK", "WARN", "BLOCK")


def _unchecked_severity(mode, stop_hook_active):
    """게이트 활성 + 미완료(미확인/결속불가) 시 severity. enforce 첫 Stop 만 BLOCK, 그 외 WARN.
    enforce 라도 stop_hook_active=true(이미 1회 block 했음)면 플랫폼 제약상 재차단 불가 → WARN 로 낮춘다.
    advisory 는 애초에 block 안 함."""
    return "BLOCK" if (mode == "enforce" and not stop_hook_active) else "WARN"


def check(mode, has_06_this_session, run_id, retro_checked, stop_hook_active, notes_enabled=True, binding="resolved"):
    """순수 함수. 입력은 전부 adapter(hook_runtime.py)가 세션/파일시스템에서 미리 계산해 넘긴다.

    mode: "off"|"advisory"|"enforce"|기타(무효 → off 취급).
    has_06_this_session: 이번 세션에 06 phase glob 매치 파일이 쓰였는가.
    run_id: 이번 세션 06 이 자기선언한 Loop-Run run_id(다중 06 은 어댑터가 worst-case 로 축약). None = 특정 불가(binding 참조).
    retro_checked: retro_audit.jsonl 에 이 run_id 의 유효 기록이 있는가.
    stop_hook_active: 이번 Stop 시도가 이전 Stop 훅의 block 때문에 생긴 재시도인가(플랫폼 제공 필드).
    notes_enabled: knowledge_capture.retro_note 가 켜져 있는가(retro 노트가 생성되는가).
    binding: 06↔05 결속 상태. "resolved"(run_id 유일) | "no_candidate"(같은 stem 05 없음/마커 없음) |
             "ambiguous"(run_id 여럿 — 다중 사이클/충돌 마커). has_06 이 true 일 때만 의미.

    반환: {"name": "retro_gate", "severity": one of _SEVERITIES, "text": str}.
    severity="BLOCK" 일 때만 오케스트레이터가 프로세스를 exit 2 로 종료해야 한다(플랫폼별 IO 모듈이 판단).
    """
    if mode not in ("advisory", "enforce"):
        return {"name": "retro_gate", "severity": "INFO", "text": "N/A — pdca.retro.report_gate_enforce=off"}
    if not notes_enabled:
        # retro_note off → 노트가 안 만들어져 `sage retro --check` 자체가 불가. enforce 는 노트 워크플로가
        # 켜져 있음을 전제하므로 게이트를 skip 한다(codex 구현리뷰 6R P1: sage-team 이 vault off 면 retro 를
        # skip 하라 안내하는데 여기서 block 하면 정상 흐름과 충돌). profile_validate 가 이 조합을 WARN 한다.
        return {"name": "retro_gate", "severity": "INFO",
                "text": "N/A — knowledge_capture.retro_note off (노트 미생성 → --check 불가, 게이트 무동작)"}
    if not has_06_this_session:
        return {"name": "retro_gate", "severity": "INFO", "text": "N/A — 이번 세션에 06 문서 작성 없음"}
    if run_id is None:
        # 이번 세션에 06 이 쓰였는데 대응 retro run 을 유일하게 특정하지 못함 = 결속 불가.
        # 조용한 INFO skip 은 게이트 우회다(외부 보완 피드백 Item 2). advisory=WARN / enforce 첫Stop=BLOCK.
        reason = ("한 06 문서에 Loop-Run 마커가 둘 이상 기록돼 run_id 모호"
                  if binding == "ambiguous"
                  else "06 문서에 Loop-Run 마커가 없어 사이클 미선언(06 에 run_id 미기록)")
        text = (f"06 작성됐으나 retro 사이클 결속 불가 — {reason}. 06 문서에 `Loop-Run: <run_id>` 를 기록했는지 확인하세요.")
        return {"name": "retro_gate", "severity": _unchecked_severity(mode, stop_hook_active), "text": text}
    if retro_checked:
        return {"name": "retro_gate", "severity": "OK",
                "text": f"retro --check 통과 확인됨 (run_id={run_id})"}

    text = (f"retro --check 미확인 (run_id={run_id}) — `sage retro --run-id {run_id} --feature <stem>` 로 "
            f"human-gate 노트를 작성·확인한 뒤 `sage retro --check <노트> --run-id {run_id}` 를 실행하세요.")
    return {"name": "retro_gate", "severity": _unchecked_severity(mode, stop_hook_active), "text": text}
