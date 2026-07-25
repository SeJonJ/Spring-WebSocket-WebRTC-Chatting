# [Base Plan] Frontend 검증 기준선 + ESLint 단계적 도입 (9-A)

Cycle-Stem: frontend_verification_eslint

Risk Level: L2
<!-- 대상 globs = scripts/**, nodejs-frontend/*.js, nodejs-frontend/static/js/**, chatforyou-desktop/build-scripts/**,
     sage/**, .github/workflows/** — 모두 profile L2 path globs. WebRTC/security/recording/game 도메인 미해당,
     L3 콘텐츠 키워드(RTCPeerConnection·MediaPipeline·JwtToken 등) 미포함. 앱 런타임 로직 변경 없음(툴링·검증 하네스만). -->

## 0. Prior Knowledge

| Type | Note | Key Takeaway |
|------|------|--------------|
| SPEC | wiki `SPEC - ChatForYou 기능 개발 우선순위 로드맵` §9-A (CFY-FB-01/02/03) | 본 사이클의 요구 원천. 완료 판단 기준을 §9-A에서 가져와 01 acceptance matrix로 고정. |
| SCAN | `.sage/knowledge_scan.md` (status: ran, 8 matches) | §9-A 외 매치는 SAGE 거버넌스 메타 문서로 tangential. 신규 설계 논거 없음 → repo 파일 기준 진행. |
| CODE | `scripts/verify-changes.sh` frontend syntax 게이트 | 현재 frontend JS 구문 검사가 존재하나 git 변경 파일 한정(diff-scoped). 전체 검증 기준선·기존 오류 baseline 부재. |
| CODE | `chatforyou-desktop/build-scripts/sync-frontend.js` (`validateEnvironment()`) | desktop web→desktop 동기화 validator. 현재 red 상태이나 원인 미확정(구현 단계 재현 대상). |

## 1. Summary (Goal & Scope)

목표: ChatForYou 프론트엔드의 **검증 기준선을 세우고 ESLint를 단계적으로 도입**하여, 회귀를 결정론적으로 감지할 수 있는 토대를 만든다. 세 건 모두 이번 사이클 범위다.

- **CFY-FB-01** — route/구문 전체 검증 기준선: 변경 파일 한정이 아닌 프론트엔드 전체 진입점에 대한 결정론적 구문 검증 기준선 확립.
- **CFY-FB-02** — desktop sync validator red baseline 복구: `sync-frontend.js`의 현재 red를 재현·특정하고 clean baseline PASS와 의도적 누락 FAIL을 각각 재현 가능하게 복구.
  - 검증은 실제 `chatforyou-desktop/src`, config, build-info, backup을 변경하지 않는다.
  - `--dry-run`은 파일 복사뿐 아니라 전체 sync 파이프라인의 모든 쓰기 경로를 차단한다.
- **CFY-FB-03** — Frontend ESLint 단계적 도입: clean slate에서 ①baseline ②warning ③변경파일 blocking 3단계까지 도입. ④ 전체 CI blocking은 legacy 정리 후 후속 사이클로 이월.

경계 원칙: 이 3건은 SAGE 범용 엔진 개발이 아니다. **ChatForYou가 검증 도구·명령·baseline을 소유·구현**하고, SAGE는 이후 profile `verification.commands`에 등록된 명령을 프로젝트 중립적으로 실행·판정할 뿐이다.

## 2. Impact Analysis (Critical)

- **[Frontend]** (`nodejs-frontend/**`): ESLint 설정·규칙셋·baseline 신규 도입(clean slate — 현재 devDeps는 concurrently·sass 뿐). route/구문 검증 대상 진입점(`server.js` + `static/js/**`) 목록화. 앱 런타임 로직은 변경하지 않는다.
- **[Desktop]** (`chatforyou-desktop/**`): sync validator 복구는 `build-scripts/` 영역만 대상. `chatforyou-desktop/src/**` 직접 수정 금지(web 공유 원본 수정 후 sync 절차 준수).
- **[검증 하네스]** (`scripts/**`): 전체 구문 검증 기준선을 위한 명령/baseline 확장. 기존 diff-scoped 게이트의 결정론 계약을 깨지 않는다.
- **[CI]** (`.github/workflows/**`): 후속 blocking 단계 대비. 이번 사이클은 로컬·changed-file blocking까지이며 전체 CI blocking은 이월.
- **[거버넌스]** (`sage/project-profile.yaml`): 실행 가능한 명령이 green으로 확정된 뒤에만 `verification.commands`(lint/syntax)에 **후반 연결**. 소유권 경계 준수.
- **[Backend]**: 앱 코드 변경 **없음**. 본 사이클에 백엔드 작업 부재.

## 3. Technology & Risks

- **결정론 요구**: 검증 명령은 같은 revision에서 반복 실행 시 동일 결과여야 한다. baseline이 실행 환경(파일 나열 순서·타임스탬프)에 흔들리면 게이트가 flaky 해진다.
- **legacy 폭발 위험**: 대규모 기존 위반을 한 번에 blocking 하면 개발이 마비된다. baseline(기존 위반)과 신규 위반을 반드시 분리한다(핵심 제약).
- **"route" 용어 불일치**: profile은 `nodejs-frontend/routes/**`를 L2 glob으로 선언하나 해당 디렉토리는 현재 존재하지 않는다. 실제 라우팅 진입점은 `server.js`이며 UI 로직은 `static/js/**`에 있다 → "전체 route"의 실질 범위 정의를 01/02에서 확정.
- **Desktop 비변형**: 현재 산출물을 임시 target에 복제하고 그 복제본에서 sync한 뒤 전후를 비교한다. 실제 Desktop target에서는 sync를 실행하지 않는다.
- **소유권 침범 위험**: SAGE 범용 엔진·`chatforyou-desktop/src` 직접 수정은 금지. 위반 시 scope change로 사용자 승인 필요.

필수 Phase(L2): 00 / 01 / 02 / 03. 독립 PDCA 사이클 `frontend_verification_eslint`.

## 4. Final Conclusion & UX Guide

개발자 관점 최종 상태: `npm run` 한 줄로 (a) 프론트 전체 구문 검증, (b) desktop sync clean/누락 재현, (c) ESLint warning 실행 + 변경파일 blocking을 각각 돌릴 수 있고, 이 명령들이 green 확정 후 profile에 등록되어 SAGE 게이트가 자동 판정한다. 사용자 확인 시나리오는 01 acceptance matrix로 고정한다.

## 5. Document Mapping (Checklist)

- [x] 기본 계획: `plan_docs/00-base_plan/2026/07/frontend_verification_eslint.md`
- [x] 요구사항/명령/제약/acceptance: `plan_docs/01-plan/frontend_verification_eslint.md`
- [x] 설계(명령·baseline 격리·ESLint rollout·profile wiring): `plan_docs/02-design/frontend_verification_eslint.md`
- [x] 구현 가이드(소유권/체크리스트/증거): `plan_docs/03-implementation/frontend_verification_eslint.md`
- [x] 갭 분석: `plan_docs/04-analyze/frontend_verification_eslint.md`
- [x] 전문가 리뷰: `plan_docs/05-expert-review/frontend_verification_eslint.md`
- [x] 최종 보고서: `plan_docs/06-report/frontend_verification_eslint.md`
