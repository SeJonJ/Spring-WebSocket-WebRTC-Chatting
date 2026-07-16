# [Base Plan] SAGE 완전 적용 (ChatForYou 재흡수 하드닝 SD-1~SD-8)

## 0. Prior Knowledge (연계 사이클)

| Type | Note | Key Takeaway |
|------|------|--------------|
| DESIGN(SSOT) | `obsidian/wiki/SAGE - ChatForYou 적용 재설계 (AGENT_GUIDE override 기반, 26.07.15)` | 본 실행 계획의 **설계 정본**. codex 5R(R1~R5) 반영, 아키텍처 결정 A/B 확정. 본 문서는 그 설계를 실행 단계(S0~S8)로 옮긴 트래커이며 설계 논거를 복제하지 않는다. |
| DESIGN(분리) | `obsidian/wiki/SAGE - SD-9 서버측 권위 게이트 보안설계 (attestation, 26.07.15)` | SD-9(서버측 diff-gate + 서명 attestation)는 별도 보안설계 track. **본 적용 범위 밖**. 배송 전까지 실제-변경 강제는 advisory. |
| CODE | SAGE 0.9.60 (`sage_project` HEAD `79ab152`), 전역 pipx `sage-harness 0.9.35`(stale) | 착수 전제 = repo 재설치/핀. 도그푸딩은 editable install. |
| BRANCH | `chatforyou_v2_sage` (chatforyou_v2 043eb85 기반, 하네스 커밋 2건 체리픽) | feat/138(#138/#141) 앱 코드는 미포함(테스트 중). 하네스 경로는 feat/138 tip과 일치. |

> 본 사이클은 앱 기능이 아니라 **하네스 거버넌스 마이그레이션**이다. ChatForYou의 수기 하네스(AGENT_GUIDE 204줄·agents 9·hooks 5·docs/agent 9)를 SAGE spec-SSOT로 역흡수하며, 그 과정에서 CFY 도그푸딩이 드러낸 SAGE 범용 결함(SD-1~SD-8)을 SAGE 소스에서 개발한다. 두 repo(`sage_project` + `ChatForYou_v2`)에 걸친다.

## 1. Summary (Goal & Scope)

목표: ChatForYou를 정식 SAGE 프로젝트로 완전 적용(dry-run 아님)한다.

- **(A)** L3 안전 도메인 = 생성형 kind 대신 손저작 AGENT_GUIDE override(`asset_overrides/framework/`) + 결정론 hook 강제.
- **(B)** CFY AGENT_GUIDE를 중립 CORE에 분해(값→profile · 트리거→profile.risk.domains · 고유 prose→override · 범용→CORE 상향).
- **(C)** SAGE 범용 하드닝 SD-1~SD-8을 editable install로 도그푸딩하며 개발 → 안정 후 SAGE upstream/릴리즈.

적용 범위 = **S0~S8** (설계 §9). adoption 최종상태 = SD-1~SD-8 + 로컬 advisory 게이트 + 자산 무결성 CI.

명시적 제외 범위:

- **SD-9(서버측 권위 attestation)** — 별도 보안설계 track. 실제-변경 서버강제는 본 사이클 밖. 그 전까지 실제-변경 강제는 advisory(§10 Trust Anchor 일관).
- feat/138(#138/#141) 앱 코드 머지 — 별도(테스트 완료 후).

## 2. Impact Analysis (Critical)

- **[Harness/거버넌스]** (주 영향): `AGENT_GUIDE.md`·`CLAUDE.md`·`CODEX.md`·`AGENTS.md`·`docs/agent/*`·`.claude/*`·`.codex/*` 전면 재편(absorb → SSOT → generate). `install --force` 충돌 인벤토리(설계 §3 표)를 S4 前 완료해야 CFY 고유 doc 소실 방지.
- **[SAGE 소스]** (`sage_project`): SD-1~SD-8 하드닝 개발. 전부 범용(다른 프로젝트에도 적용). 결정론 계약(설계 §4 R4 확정 계약)대로 구현.
- **[Backend/Frontend/Desktop 앱코드]**: **직접 변경 없음.** 단 WebRTC L3 안전 계층이 parity는 통과하나 의미적으로 약해질 위험(설계 §8) → hook 강제(SD-1/2) + review 매칭(SD-8) + critical-domains/webrtc.md 보존으로 다층 방어.
- **[CI]**: `.github/workflows`에 자산 무결성 job(SD-5 strict allowlist) 추가(S8). 실제 PR-diff 게이트(SD-9)는 별도 track.
- **[Deploy]**: `GitAction-k8s-deploy.yml` 변경 없음(#141 앱 커밋 소관, 본 사이클 밖).

## 3. Technology & Risks

Risk Level: **L3** (거버넌스/하네스 자체 재편 + WebRTC L3 안전 계층 정합성)

Reason:

- 변경 대상이 **모든 후속 작업을 지배하는 하네스**이며, WebRTC L3 안전 계층의 강제 경로(hook·review-oracle)를 재구성한다 → 최고 주의.
- 핵심 함정(설계 §5): 등록 `sage-hook` 경로가 SAGE_PROFILE 미주입 → **트리거 강제는 SD-1 착수 전엔 미가동**. SD-1 전까지 어떤 enforcement도 신뢰 금지(fail-open).
- 범용 원칙(cross-model P0 다운그레이드 금지): codex가 원리결함으로 지목한 SD-1/SD-8(P0)는 완화가 아니라 정면 해결.
- 필수 Phase: **00~06** (저장소 `AGENT_GUIDE.md` L3 계약. SAGE 소스 개발분은 단위/E2E 증거 필수 — 등록경로 hook E2E 회귀가드 포함).
- 독립 PDCA: 신규 `sage_adoption` 사이클. 기존 사이클 재사용 금지.

## 3-1. 핵심 설계 결정 (설계 SSOT에서 확정)

설계 5R로 확정된 결정은 vault SSOT에 있으며 여기서 재론하지 않는다. 실행상 불변(하드-원):

- absorb-first (덮어쓰기 아님) · target별 hook 명세 · 9 agent→roster 역분해 · **§10 Trust Anchor(권위=CI+branch protection, 로컬=advisory)**.
- **착수 시 결정 필요(설계 R5 잔여):** CFY `verify-changes.sh` rich 로직(diff/untracked 수집·component/risk 자동분류·per-file 검사·URL-prefix·`--base`·degraded/block exit)의 최종 목적지 = **project-local 스크립트(LOCAL)** vs `verification_gate` core 능력 승격. → S1 인벤토리에서 확정.

## 4. Execution Sequence & Ownership (S0~S8)

| 단계 | 내용 | 담당 | 게이트 |
|------|------|------|--------|
| **S0** | 전용 브랜치 + SAGE 0.9.60 editable install + `sage doctor` | Claude | 브랜치 격리·버전 핀 |
| **S1** | inventory — 하드코딩 트리거·agent 조항·hook 로직차 + **install --force 충돌 인벤토리**(설계 §3, S4 前 필수) + verify-changes.sh 목적지 확정 | Claude | 충돌 인벤토리 전수 |
| **S2** | absorb (dry) hook/agent/skill → spec draft (docs는 분해; 충돌 doc 네임스페이스 선이전) | Claude | absorb 보존 oracle(§6, 없으면 수기 체크리스트) |
| **S3** | `project-profile.yaml` — risk 트리거 + risk.domains 레지스트리(SD-4) + content_l3_enforce=block(SD-2) + components + verification + l3_review_strategy | Claude | 인스턴스 확정값(설계 §1) |
| **S4** | AGENT_GUIDE 분해 — 중립 CORE(SD-3 override-read 문장) + framework override 저작 | Claude | 충돌 doc 이전 완료 후 |
| **SD-1** | 게이트 hook **fail-closed** profile 로드 (P0, SAGE 소스) | Claude | accept 매트릭스(양 host × 5조건) |
| **S5** | `sage generate --kind hook/agent/skill --target both` (write) + profile YAML→JSON 컴파일 확인 | Claude | SD-1 fail-closed hook 등록 |
| **SD-2/SD-8** | content-L3 BLOCK(P0) + review-oracle 강화(P0) (SAGE 소스) | Claude | 명시적 BLOCK 규칙(설계 §8) |
| **S6** | content-L3 BLOCK + review-oracle + C1 fixtures(양 target) ★로컬 게이트 | Claude | fixture 통과 |
| **S7** | cross_model 완전 배치(SD-6 installed_hosts) + .codex 검증 + obsidian + codegraph | Claude | 양 discovery 표면 |
| **S8** | 자산 무결성 CI(SD-5 allowlist) + hook E2E(등록경로 회귀가드) + framework override --force 생존 + build-id source대조 + branch protection | Claude | required status checks |
| ─ | **SD-9 서버 권위** = 별도 track(시퀀스 밖) | (분리) | — |

> SD-3/SD-4/SD-7은 S1~S8에 걸쳐 각 단계에 편입(설계 §4). SAGE 소스 개발분은 **`edit SAGE → sage install --force → generate → validate → 등록경로 E2E`** 도그푸딩 루프 + source build-id 추적(설계 §14).

## 5. Document Mapping

- [x] 기본 계획: `plan_docs/00-base_plan/2026/07/sage_adoption_plan.md`
- [x] 요구사항/인벤토리: `plan_docs/01-plan/sage_adoption.md` (S1 산출 — 충돌 인벤토리 전수표)
- [x] 설계/시퀀스: 설계 SSOT(vault)로 갈음 + `plan_docs/02-design/sage_adoption.md`(실행 세부만)
- [x] 구현 가이드: `plan_docs/03-implementation/sage_adoption.md`
- [x] SAGE 소스 개발 가이드: `sage_project/plan_docs/overlay-composition-plan.md`
- [x] 갭 분석: `plan_docs/04-analyze/sage_adoption.md`
- [x] 전문가/cross-model 리뷰: `plan_docs/05-expert-review/sage_adoption.md` (초기 REJECTED 결함 수정 후 APPROVED_WITH_RISK; 원격 CI 전제만 잔존)
- [x] 최종 보고서: `plan_docs/06-report/sage_adoption.md` (Wiki 심층 write-back, loop dashboard, retro check까지 2026-07-17 완료)

## 6. Workflow Gate (L3)

- [x] Pre-Implementation Compliance Gate 선언 (Risk L3 / 하네스 거버넌스 / phase 00-05 / 본 plan 경로 / 설계 SSOT codex 5R 완료)
- [x] 설계 게이트: codex 5R(R1~R5) 반영 → SSOT 확정 (설계 §13)
- [x] S0 브랜치 + editable install + doctor
  - 2026-07-16: `chatforyou_v2_sage`, pipx `sage-harness 0.9.60` editable source=`/Users/sejon/project/sage_project`, `sage doctor` exit 0.
  - ChatForYou profile 미설치 상태라 doctor는 `sage_project/templates/project-profile.yaml`을 검사했다. 프로젝트 profile 검증은 S3 이후 재실행한다.
- [x] S1 인벤토리 (install --force 충돌 전수 + verify-changes.sh 목적지)
  - 충돌 목적지는 `plan_docs/01-plan/sage_adoption.md` §5에 고정. rich `verify-changes.sh`는 project-local 유지.
- [x] S2 absorb (dry) + 보존 oracle
- [x] S3 project-profile.yaml (임시 확정; Phase 06 전 사용자 재인터뷰 필수)
- [x] S4 AGENT_GUIDE 분해 + framework override
- [x] SD-1 fail-closed hook (P0) + accept 매트릭스
- [x] S5 generate (write) + YAML→JSON 컴파일
- [x] SD-2/SD-8 (P0) + S6 로컬 게이트 + C1 fixtures
- [x] S7 cross_model 완전 배치 (SD-6)
- [ ] S8 자산 무결성 CI 코드 + hook E2E + build-id 완료; 원격 branch protection 미확인
- [x] SAGE 개발분 독립 sub-agent + true Claude clean-context 검증 및 rework
- [x] vault knowledge capture
- [x] 최종 project-profile 사용자 재인터뷰 + 승인 + 재생성/재검증

## 7. Branch

`chatforyou_v2_sage` (chatforyou_v2 043eb85 기반). 하네스 커밋 `7093b90`·`e8468b1` 체리픽 완료 → 하네스 경로가 feat/138 tip과 일치(absorb 입력 최신화). SAGE adoption 검증 후 default 브랜치를 chatforyou_v2_sage로 전환 예정. SAGE 소스 개발분은 `sage_project` repo에서 별도 진행.
