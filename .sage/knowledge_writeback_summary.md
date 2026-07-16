> [!abstract] 핵심 Takeaway (백엔드/인프라 설계 및 업무 효율화 관점)
> - ChatForYou 실프로젝트에 SAGE를 역적용하면서 profile fail-closed, 양 host 생성 자산, L3 도메인 레지스트리, 독립 리뷰와 검증 폐루프를 실제 운영 가능한 수준으로 완성했다.
> - 이번 사이클의 가장 큰 성과는 모든 한계를 억지로 해결한 것이 아니라, 검증된 도입 범위와 새 엔진 개발이 필요한 피드백을 분리해 현재 결과를 `APPROVED_WITH_RISK`로 정직하게 닫은 것이다.

## 배경과 근본 원인

ChatForYou는 SAGE의 출발점이 된 풍부한 수기 에이전트 하네스를 이미 가지고 있었지만, 기존 SAGE를 그대로 설치하면 프로젝트 고유 규칙이 CORE 파일과 충돌하고 양 런타임의 생성 자산 및 profile 게이트가 실제 등록 경로에서 동일하게 동작한다는 보장이 없었다. 특히 등록 `sage-hook`의 profile 부재·파손·YAML/JSON drift가 fail-open될 수 있었고, content 기반 L3 분류와 과거 리뷰 문서 재사용 방지, 다중 host 설치 상태, framework override 생존성도 실프로젝트 기준으로 부족했다.

이 문제는 단순한 ChatForYou 설정 이전이 아니라 SAGE 범용 엔진의 결함을 실증하는 작업이었다. 따라서 ChatForYou 애플리케이션 코드를 건드리지 않고, 범용 SAGE 하드닝과 프로젝트 profile/override/critical-domain 구성을 한 사이클에서 검증했다.

## 설계 결정

1. ChatForYou 고유 값은 `sage/project-profile.yaml`과 `sage/critical-domains/*.md`, `sage/asset_overrides/framework/*.md`에 둔다.
2. 공유 판단 알고리즘에는 ChatForYou 도메인 값을 넣지 않고 profile compiler가 L1-L3 경로와 content keyword를 런타임 JSON으로 물리화한다.
3. Claude와 Codex는 같은 의미 계약을 사용하지만 각 런타임의 등록·입력·출력 차이는 adapter에서 유지한다.
4. L3 도입 범위는 WebRTC, Security/Auth, Recording lifecycle, ChatForYou Game으로 확정한다.
5. 최종 profile 인터뷰에서 표현할 수 없는 기능은 inert 설정으로 위장하지 않고 새 SAGE 개발 사이클의 요구사항으로 분리한다.

## 변경 내역

- `sage/hook_entry.py:main`과 `scripts/sage_harness/hooks/runtime/hook_runtime.py` 계층에서 등록 hook의 profile fail-closed 및 source/runtime 결속을 강화했다.
- `sage/profile_compile.py:materialize_profile`에서 `risk.domains`를 런타임 flat L3 경로·키워드로 컴파일한다.
- `scripts/sage_harness/hooks/pre_implementation_gate_core.py:_classify_one`과 review 전략에서 content-L3 provenance 및 cycle/domain/round 리뷰 증거를 검증한다.
- `sage/overlay_materialize.py`와 `sage/commands/sync_overlays.py`에서 양 host preflight 후 atomic apply, host별 receipt 병합, source/version skew 차단을 구현했다.
- `sage/project-profile.yaml`에 backend/frontend 두 컴포넌트, 네 L3 도메인, L1 advisory/L2-L3 block 검증, vault/loop/retro 설정을 확정했다.
- `sage/critical-domains/recording.md`와 `sage/critical-domains/game.md`를 추가하고 기존 WebRTC/Security 프로토콜과 함께 doctor가 네 포인터를 검증하도록 했다.
- `docs/chatforyou-agent/knowledge-capture-fallback.md`와 framework override에 vault 장애 시 `.sage/pending-wiki/` 초안 보존 계약을 추가했다.
- Phase 01 acceptance matrix와 Phase 04 evidence를 `SAGE-ADOPT-01`~`08` ID로 결속했다.
- 최종 review-loop `rl-699465499cba`는 2회차에 수렴해 `APPROVED/CONVERGED`로 종료됐다.

## 검증

- SAGE 전체 테스트: `1027 passed, 1 skipped, 57 subtests`.
- native write-guard: `61/61`.
- ChatForYou 등록 hook acceptance: `16/16`.
- Claude/Codex hook 회귀: `22/22`, `23/23`.
- verification smoke: `9/9 + 4/4 + 6/6`.
- 최종 `sage validate --check --schema --strict --kind all`: exit 0, schema/profile PASS.
- `sage doctor`: 양 host CORE 최신, WebRTC/Security/Recording/Game 포인터 정상.
- `scripts/verify-changes.sh --level L3`: 문서/profile 종료 diff에 대해 PASS/N/A, exit 0.
- 최종 cross-model Claude 호출은 두 번 모두 exit 1로 실패했다. 이를 숨기지 않고 clean-context same-runtime 독립 리뷰로 degrade했으며, 첫 라운드 P1 2건 중 acceptance 구조를 보강하고 ticketless 결속 한계는 사용자 승인 아래 별도 개발로 분리했다. 두 번째 라운드는 finding 0으로 수렴했다.

## 재발 방지와 후속 개발

현재 도입 사이클의 잔여 위험은 완료 결과와 분리된 새 SAGE PDCA로 다룬다.

- L0-first 분류에서 일반 이미지는 L0로 유지하면서 WebRTC/Game 전용 이미지만 L3로 올릴 수 있는 exclusion/priority 기능.
- Acceptance의 L2 advisory, L3 enforce 및 운영 배포·외부환경 검증에 대한 명시적 사용자 waiver.
- 실제 활성 host 기준 opposite-runtime reviewer routing과 Manual Double-Host Resume 정식 지원.
- host별 모델 후보·사용자 선택 및 cross-review 모델 명시 설정.
- 자동 context snapshot/restore와 compaction 결속.
- Codex 프로젝트/전역 SAGE 스킬 중복을 제거하는 설치 scope와 팀 온보딩 모델.
- ticket 없는 브랜치에서도 최근 문서가 아니라 cycle stem으로 Phase 01/04/05를 결정론적으로 결속하는 기능.
- Frontend 전체 route syntax, Desktop sync validator 기준선 복구, 단계적 ESLint 도입.
- 원격 SAGE ref 발행, CI 실행, branch protection required check는 외부 전달 게이트로 유지한다.

## 관련 문서

- [[SAGE - 통합 마스터 설계]]
- [[SAGE - 앞으로 개발할 내용]]
- [[SAGE - 프로젝트 실증 테스트 인덱스]]
- [[SAGE - 프로젝트 실증 테스트 2차 (ChatForYou 적용 설계, 26.07.11)]]
- [[SAGE - SD-9 서버측 권위 게이트 보안설계 (attestation, 26.07.15)]]
- sage_adoption_plan.md
- sage_adoption.md (Phase 01-06)
