# [Base Plan] Bug #136 — 배포/종료 중 녹화 중단 시 partial 녹화 파일 정리

## 0. Prior Knowledge (연계 사이클)

| Type | Note | Key Takeaway |
|------|------|--------------|
| CYCLE | bug_135_recording_inprogress (완료·머지, PR #142) | 중단 녹화의 in-progress 상태를 stopped 로 reset. reset 직전 파일 식별 정보를 별도 Redis 키 `room:recording:partial:{roomId}` 에 마커로 보존. #136 은 이 마커를 소비한다. |
| SPEC | 무중단 배포 복구 설계 | `partial recording file 정책`은 #135 에서 명시적으로 #136 으로 분리됨. |

> 본 사이클은 #135 에서 심어둔 partial 마커 인프라를 소비하는 **신규 후처리 기능**이다. #135 의 녹화 상태 reset 로직은 재사용/변경하지 않는다.

## 1. Summary (Goal & Scope)

배포(Rolling Update) 또는 Pod 종료로 방 녹화가 중단되면 KMS 컨테이너의 로컬 mp4 는 finalize/remux 없이 남는다(재생 불가 partial). #135 는 이 파일의 식별 정보를 `room:recording:partial:{roomId}` 마커에 보존만 했고, 실제 파일 정리는 미구현이다.

목표:

- 주기적 배치가 partial 마커를 스캔하여 일정 나이(age) 이상 경과한 대상의 partial 파일을 삭제한다.
- 로컬 PVC(RWX NFS) 파일 삭제 + (존재 시) MinIO 객체 삭제.
- 삭제 사실을 `download_log` 테이블에 "시스템 자동 삭제" 상태로 기록한다.
- 정리 완료 후 마커를 명시적으로 삭제한다(TTL 자연 만료 대기 X).

확정 정책 (유저 승인 완료):

1. remux/finalize 없음 — partial mp4 는 복구 시도 없이 삭제 대상으로만 취급.
2. 비노출 — partial 파일은 목록/다운로드 UI 에 노출하지 않음(#135 재입장 "녹화 중단" 메시지로 충분).
3. 삭제 기준 — 크기/길이 임계값 없이 무조건 삭제(마커 나이 기준).
4. 배치 스캔 주기 — 1시간.
5. `DownloadLog` 에 "시스템 자동 삭제" 구분용 신규 상태값 추가.

명시적 제외 범위:

- partial 파일 재생 복구(remux/finalize) — 하지 않음.
- FE 노출/다운로드 — 하지 않음(비노출).

## 2. Impact Analysis (Critical)

- [Backend]: 영향 범위가 전적으로 백엔드에 한정된다.
  - `webChat/batch/` — 신규 배치 잡. `RoomBatchJob` 패턴(`@Scheduled` cron + `@SchedulerLock`) 준수. RWX NFS 를 3 replica 가 공유하므로 동시 삭제 경합 방지 위해 shedlock **필수**.
  - `webChat/service/redis/RedisService(+Impl)` — partial 마커 전체 목록을 가져오는 신규 스캔 메서드. 기존 `getKeysByPattern`(slaveTemplate, SCAN 기반)·`getChatRoomListForDelete` 패턴 참조. 마커 키 패턴 = `room:recording:partial:*`.
  - `webChat/service/recording/` — 신규 정리 서비스. 스캔→age 필터→로컬 파일 삭제→MinIO 삭제(방어)→DownloadLog 기록→마커 삭제 오케스트레이션.
  - `webChat/entity/DownloadLog.java` — `DownloadStatus` enum 에 시스템 자동 삭제 신규 값 추가. system-deletion 로그용 factory 보강 가능.
  - `webChat/service/monitoring/DownloadLogService(+Impl)` — system-deletion 로그 저장 경로(기존 `saveDownloadLog` 재사용 가능).
  - 참조(재사용): 로컬 파일 삭제 패턴 = `RecordingUploadService`/`RecordingFileService` 의 `localFilePath.replace("file://","")` → `new File(cleanPath).delete()`. MinIO 삭제 패턴 = `AbstractFileService.deleteFileDir` 의 `minioClient.removeObject(RemoveObjectArgs)`.
- [Frontend]: **변경 없음.** partial 녹화는 이미 어떤 목록에도 노출되지 않는다 — #135 가 `recordingInfo` 를 null 로 reset 했고, partial 은 MinIO 업로드 전 중단이라 `minioFilePath` 가 비어 있으며, `download_log` 에 SUCCESS 로 기록된 적이 없다. 따라서 비노출 정책은 신규 FE 코드 없이 이미 충족된다.
- [Desktop]: 영향 없음. FE 변경이 없으므로 Electron sync 불필요.
- [Infra/Deploy]: manifest 변경 없음. 신규 배치는 기존 스케줄러 인프라(shedlock 테이블) 위에서 동작. 신규 config property 2개(cleanup age, cron) 추가.

## 3. Technology & Risks

Risk Level: **L2**

Reason:

- 변경 지점이 **Redis 상태(마커 스캔/삭제) + 파일시스템/MinIO 삭제 + DB 영속(DownloadLog)** 이다 → `AGENT_GUIDE.md` §3 L2(Backend state / Redis / persistence).
- WebRTC / WebSocket / Signaling / Kurento / room lifecycle / Desktop **변경 없음** → L3 아님. 본 기능은 #135 가 심은 마커를 **소비만** 하며 녹화 시그널링·미디어 파이프라인을 건드리지 않는다.
- 추가되는 코드는 대부분 additive(신규 배치·신규 스캔 메서드·enum 값 추가·신규 서비스)로 기존 시그널링 심볼을 수정하지 않는다.
- Compound rule applied: no.
- 독립 PDCA: 기존 `bug_135` 사이클 재사용 금지 — 본 신규 `bug_136` 사이클로 진행.
- 필수 Phase: **00~05** (빌드·테스트 증거 필수).

## 3-1. 핵심 설계 결정 (유저 승인 완료 — 2026-07-05 확정)

- **(OPEN-1 확정)**: 옵션 A 채택. 삭제 임계값 = **4시간**, 신규 property `recording.partial.cleanup.age-seconds=14400`. 마커 TTL 은 6시간(21600s) 그대로 유지, #135 인프라(RedisServiceImpl TTL 소유) 변경 없음.
- **(OPEN-2 확정)**: `DownloadStatus` 신규 값 = **`SYSTEM_AUTO_DELETED`** (유저 직접 지정).

아래는 결정 근거 기록(참고용).

### (OPEN-1) 마커 TTL vs 삭제 age 임계값 경합 — 확정: 옵션 A (4h)

승인된 정책 5번은 "markedAt 기준 경과시간이 TTL(6h) 이상이면 삭제"지만, 마커 Redis TTL 자체가 6h(`recording.partial.marker.ttl-seconds=21600`, RedisServiceImpl 단독 소유)다.

문제: **Redis 가 6h 시점에 마커 키를 자동 evict** 하므로, "age >= 6h" 조건의 배치는 살아있는 마커를 거의 만나지 못한다. 마커가 먼저 사라지면 파일을 가리키는 포인터가 없어 partial 파일이 **영구 orphan** 이 된다(NFS 에 파일만 남고 삭제 트리거 소멸). 즉 삭제 age 임계값은 반드시 **마커 TTL 보다 작아야** 기능이 성립한다.

부가 결합: 마커는 #135 재입장 "녹화 중단" 메시지의 수명도 겸한다(`notified` 플래그). 배치가 임계값 시점에 마커를 삭제하면 그 이후 재입장 사용자는 메시지를 못 본다 → 메시지 노출 창 = 삭제 임계값.

| 옵션 | 삭제 age 임계값 | 마커 TTL | 재입장 메시지 창 | #135 config 변경 | 비고 |
|---|---|---|---|---|---|
| **A (권장)** | 신규 `recording.partial.cleanup.age-seconds` = 예 4h | 6h 유지 | 4h | 없음 | 배치 주기 1h 이므로 임계값~TTL 사이 2h(2회 실행) 여유 → 모든 마커를 TTL evict 전 확실히 처리 |
| B | 6h | ~8h 로 상향 | 6h | **있음** (#135 TTL 변경) | "6h" 문구에 충실하나 #135 인프라 config 수정 필요 |
| C | 짧게(예 1~2h) | 6h 유지 | 1~2h | 없음 | 파일은 pod 사망 시 이미 dead 라 조기 삭제 무해하나 메시지 창이 짧음 |

권장: **옵션 A**. 삭제 임계값을 마커 TTL 보다 작은 별도 property 로 두어 배치가 TTL evict 전에 확실히 마커를 소비하게 하고, #135 인프라(6h TTL)는 그대로 둔다. 임계값 구체 수치(4h 제안)는 유저 확정 필요.

### (OPEN-2) DownloadLog 신규 상태값 명칭 + 필드 매핑 — 확정: `SYSTEM_AUTO_DELETED`

- 신규 `DownloadStatus` 값 = **`SYSTEM_AUTO_DELETED`** (확정). UPPER_SNAKE_CASE 컨벤션 준수.
- 마커는 `recordingUserId`(String), `recordingNickName` 만 보유하고 `userIdx`(Long)/`email` 는 없다. 따라서 system-deletion 로그: `userIdx=null`, `email=null`(또는 recordingUserId 매핑), `roomId=marker.roomId`, `targetType=RECORDING`, `targetId=recordingId`, `fileName=marker.fileName`, `filePath=marker.filePath`(또는 minioFilePath), `status=SYSTEM_AUTO_DELETED`. 구체 매핑은 백엔드 전문가 상세 설계 시 확정.

## 4. File Ownership (제안 — 유저 승인 후 확정)

| 파일/영역 | 담당 |
|------|------|
| `webChat/batch/RecordingPartialCleanupBatchJob.java` (신규, `@Scheduled` 1h + `@SchedulerLock`) | 백엔드 전문가 |
| `webChat/service/recording/` 신규 정리 서비스 (스캔→age필터→파일삭제→MinIO삭제→로그→마커삭제) | 백엔드 전문가 |
| `webChat/service/redis/RedisService(+Impl)` partial 마커 전체 스캔 메서드 (`room:recording:partial:*`) | 백엔드 전문가 |
| `webChat/entity/DownloadLog.java` (`DownloadStatus` 신규 값 + system-deletion factory) | 백엔드 전문가 |
| `webChat/service/monitoring/DownloadLogService(+Impl)` (system-deletion 로그 저장) | 백엔드 전문가 |
| config property (`recording.partial.cleanup.age-seconds`, cron) | 백엔드 전문가 |
| `springboot-backend/plan_docs/bug_136_recording_partial_cleanup.md` (full code guide) | 백엔드 전문가 |
| `springboot-backend/src/test/**` (age 경계·minioFilePath null 방어·마커 파일 부재 방어·로그 기록·SchedulerLock 시나리오·통합) | QA 전문가 |
| Frontend | **해당 없음** (비노출 정책 이미 충족) |

## 5. Document Mapping

- [x] 기본 계획: `plan_docs/00-base_plan/2026/07/bug_136_recording_partial_cleanup_plan.md`
- [x] 요구사항 및 데이터: `plan_docs/01-plan/bug_136_recording_partial_cleanup.md`
- [x] 인터페이스 및 시퀀스: `plan_docs/02-design/bug_136_recording_partial_cleanup.md`
- [x] 구현 가이드: `plan_docs/03-implementation/bug_136_recording_partial_cleanup.md`
- [x] 백엔드 구현 가이드: `springboot-backend/plan_docs/bug_136_recording_partial_cleanup.md`
- [ ] 프론트 구현 가이드: 해당 없음 (FE 변경 없음)
- [x] 갭 분석: `plan_docs/04-analyze/bug_136_recording_partial_cleanup.md`
- [x] 전문가 리뷰: `plan_docs/05-expert-review/bug_136_recording_partial_cleanup.md`
- [x] 최종 보고서: `plan_docs/06-report/bug_136_recording_partial_cleanup.md`

## 6. Workflow Gate (L2)

- [x] Pre-Implementation Compliance Gate 선언 (Risk L2 / compound no / phase 00-05 / 본 plan 경로 / BE-only impact)
- [x] **OPEN-1(TTL/임계값=4h) + OPEN-2(상태값=SYSTEM_AUTO_DELETED) 유저 결정 완료** (2026-07-05)
- [x] Phase 01 요구사항 + 데이터(신규 enum 값·config) 작성
- [x] Phase 02 design (배치 시퀀스 + 검증 시나리오)
- [x] Phase 03 구현 (BE) — 빌드·테스트·컨벤션 통과
- [x] Phase 04 gap 분석
- [x] Phase 05 자체 재검토 (Claude 미사용: 토큰 부족으로 인한 Codex 개발/자체 재검토 전환)
- [ ] vault knowledge capture (또는 해당 없음 — 이유 명시)

## 7. Branch

현재 `bug/136` 브랜치에서 작업(#135 sourcery-ai 리뷰 반영 커밋 `a96fc2c` 이미 완료). 별도 워크트리 없이 이 브랜치에서 진행.
</content>
</invoke>
