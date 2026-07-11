# [Base Plan] 채팅방 발언자 하이라이트 (#141)

## 0. Prior Knowledge (Vault Scan)

| Type | Note | Key Takeaway |
|------|------|--------------|
| SPEC | ChatForYou 기능 개발 우선순위 로드맵 (#9) | 이미 P1로 등재. 유저가 개발 순서 확정: #138 WebRTC 프론트 리팩토링 → #141 하이라이트. "리팩토링된 구조 위에 얹는 게 안전". 영향 파일 3개 지목(kurento-service.js / AudioMixer.js / participant.js). 권장 접근 = AnalyserNode 부착 → 레벨 측정 → `.participant` 컨테이너에 speaking 클래스 토글, AudioMixer의 AudioContext 패턴 재사용 |
| TECH | ChatForYou WebRTC 프론트 파일 분리 구조 | `recording` 전역 객체(녹화 + AudioMixer) 구조. rtc/ 로드 순서 존재 — 신규 파일 삽입 시 로드 순서 고려 필요 |
| BUG | WebRTC 원격 오디오 이중 재생 | 원격 오디오는 audio element가 단독 재생, video는 항상 muted. 발화 감지 tap 은 재생 sink 가 아닌 별도 MediaStreamSource 로 분리해야 재생에 영향 없음 |
| BUG | kurento-service.js Peer 에러 Fallback 누락 | peer 생성 실패 시 자원 누수 전례. 신규 AnalyserNode/AudioContext 도 실패·정리 경로를 반드시 갖춰야 함 |
| — | 메모리 `feedback_webrtc_reconnect_first_join` | 재연결 시 스트림 재부착 발생 → analyser 재바인딩/정리 누락 시 leak. lifecycle 설계 필수 |

## 1. Summary (Goal & Scope)

**목표**: 다자간 화상채팅에서 각 참가자가 마이크로 말할 때 해당 참가자 타일을 시각적으로 하이라이트하여, "누가 말하고 있는지"를 실시간으로 식별 가능하게 한다. (GitHub Issue #141)

**해결하려는 문제**: 현재 발화 감지가 전혀 없어, 유저가 말을 안 하는 건지 말은 하는데 상대가 못 듣는 건지 구분 불가 → 사용성 저하. 사용자 반복 요청 기능.

**범위 (In)**:
- 로컬 사용자 + 원격 참가자 전원의 입력 오디오 레벨을 측정하여 발화 여부 판정
- 발화 중인 참가자의 `.participant` 타일에 하이라이트(테두리 글로우) 토글
- 참가자 입장/퇴장/재연결/방 나가기에 대응하는 자원 lifecycle 관리

**범위 (Out)**:
- 백엔드/시그널링/Kurento 서버 변경 없음 (순수 클라이언트 측 오디오 분석 + CSS)
- 발화 통계 서버 전송, 발화 로그 저장, "손들기"류 별도 기능 없음
- #138 리팩토링 자체(별개 이슈) — 본 기능은 그 위에 얹음

## 2. Impact Analysis (Critical)

- **[Backend]**: 영향 없음. API/시그널링 메시지/Kurento 파이프라인 변경 없음.
- **[Frontend]**: 영향 있음. 신규 발화 감지 모듈 + participant 타일 하이라이트 토글 + 스트림 tap 지점 연결(로컬/원격) + lifecycle 정리. 신규 CSS(speaking 클래스) 1개.
- **[Desktop]**: sync 필요. nodejs-frontend 변경분이 `chatforyou-desktop`으로 sync됨 → `npm run sync` 로 Electron 빌드 무오류 확인 필수. SCSS 신규 규칙 추가 시 `npm run scss:build` 후 sync.

**Before → After**:
- Before: 발화 감지/하이라이트 코드 전무. `participant.js`의 volume은 재생 음량 슬라이더일 뿐 입력 레벨 분석이 아님. `AudioMixer.js`는 녹화용 AudioContext만 생성(AnalyserNode 없음).
- After: 공유 AudioContext에 참가자별 AnalyserNode 부착, 단일 rAF 루프로 RMS 측정, 임계값+디바운스로 `.participant`에 `speaking` 클래스 토글.

## 3. Technology & Risks

**기술 선택 (유저 확정)**:
- 발화 감지: **Web Audio API `AnalyserNode`** (A안). 공유 `AudioContext` 1개 + 단일 `requestAnimationFrame` 루프로 전 참가자 순회, RMS 임계값 + 디바운스. 로컬/원격 통합 코드 경로. `AudioMixer.js`의 `AudioContext` 생성 패턴 재사용. 외부 라이브러리(hark.js 등) 미도입.
- UI: `.participant` 컨테이너에 `speaking` 클래스 토글 → `box-shadow` 글로우(`$color-primary`). 발화 종료 후 ~200–300ms 디바운스. **신규 SCSS 클래스** 추가(유저 확정).

**Risk Level: L3** (Phase 00~06, WebRTC 2-round 설계 리뷰 필수).
- 근거: WebRTC 미디어 스트림/피어 lifecycle 영역(`kurento-service.js` onaddstream, `participant.js` dispose)에 직접 접근. 시그널링/SDP 변경은 없으나 AudioContext/AnalyserNode 자원 lifecycle + 재연결 시 재바인딩 실패가 핵심 실패 모드. AGENT_GUIDE §3 "불확실 시 상향" 적용.

**주요 리스크**:
| # | 리스크 | 완화 |
|---|---|---|
| R1 | rAF 폴링이 참가자 수 비례 CPU 부하 | 공유 AudioContext + 단일 rAF 루프로 전 참가자 순회(참가자당 루프 X). FFT size 축소, 필요 시 폴링 간격 throttle |
| R2 | 재연결 시 스트림 재부착 → analyser leak / 중복 / stale cleanup | userId 키 Map, 재부착 시 기존 analyser disconnect 후 재생성, attach token으로 오래된 participant dispose가 새 entry 삭제 불가 |
| R3 | 참가자 퇴장/방 나가기 시 자원 미해제 | participant.dispose() + teardownRoomSession() 에 정리 훅. 모든 소스 제거 시 rAF 중단, AudioContext close |
| R4 | 로컬 송신 마이크 mute 상태에서 오탐 | sender audio track enabled=false 시 speaking 판정 스킵. 원격 수신 mute는 audio element mute로 분리해 상대 발화 표시 유지 |
| R5 | 자동재생 정책으로 AudioContext suspended | AudioMixer와 동일하게 state==='suspended' 시 resume. tap 은 재생 sink 와 무관하므로 재생에 영향 없음 |
| R6 | 임계값 오탐/과민(배경소음, 에코) | RMS 임계값 + 디바운스(상승 즉시 / 하강 지연) 튜닝. 상수로 분리해 조정 용이 |

## 4. Final Conclusion & UX Guide

- 발화 시 타일 테두리가 `$color-primary` 글로우로 즉시 켜지고, 발화가 멈춘 뒤 ~200–300ms 유지 후 꺼진다(깜빡임 방지).
- 로컬/원격 동일하게 동작. 내 송신 마이크 mute 시 내 하이라이트는 꺼지고, 상대 오디오를 로컬에서 mute해도 상대 발화 하이라이트는 유지된다.
- CPU 부하는 단일 rAF 루프로 억제. 성능 이슈 관측 시 임계값/폴링 간격 상수로 조정.
- 브랜치(2026-07-10 갱신): feat/141 로 분리하지 않고 feat/138 브랜치 그대로 하나로 묶어서 머지. #138·#141 이 같은 파일(kurento-service.js/participant.js/AudioMixer.js 스코프)을 건드리고 실기기 다자 테스트도 통합 검증이 더 현실적이라는 판단. 단 커밋은 #138/#141 로 분리해 리스크 성격이 다른 두 변경(무위험 리팩토링 vs QA 잔여 신규기능)을 bisect/롤백 가능하게 유지. 상세: wiki `SPEC - ChatForYou 채팅방 발언자 하이라이트` §0. (팀은 commit/push 직접 안 함 — 유저 직접 수행)

## 5. Document Mapping (Checklist)

- [x] 기본 계획: `plan_docs/00-base_plan/2026/07/speaker_highlight_plan.md`
- [x] 요구사항 및 데이터: `plan_docs/01-plan/speaker_highlight.md`
- [x] 인터페이스 및 시퀀스: `plan_docs/02-design/speaker_highlight.md`
- [x] 프론트 구현 가이드: `nodejs-frontend/plan_docs/speaker_highlight_plan.md`
- [x] 구현 가이드(파일 소유권/체크리스트/빌드): `plan_docs/03-implementation/speaker_highlight.md`
- [x] 갭 분석: `plan_docs/04-analyze/speaker_highlight.md`
- [x] 전문가 리뷰: `plan_docs/05-expert-review/speaker_highlight.md` — 최종 판정 APPROVED
- [x] 최종 보고서: `plan_docs/06-report/speaker_highlight.md`
- 백엔드 구현 가이드: N/A (백엔드 영향 없음)
- [x] vault knowledge capture 완료 (해당 없음 — 별도 vault note 생성 요청 없음, 06-report에 N/A 사유 기록)
