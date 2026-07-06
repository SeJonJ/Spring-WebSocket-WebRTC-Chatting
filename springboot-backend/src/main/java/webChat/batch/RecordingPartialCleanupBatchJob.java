package webChat.batch;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import net.javacrumbs.shedlock.spring.annotation.SchedulerLock;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import webChat.exception.ChatForYouException;
import webChat.service.recording.CleanupResult;
import webChat.service.recording.RecordingPartialCleanupService;

@Component
@Slf4j
@RequiredArgsConstructor
public class RecordingPartialCleanupBatchJob {

    private final RecordingPartialCleanupService recordingPartialCleanupService;

    /**
     * 중단된 방 녹화의 partial 파일을 매시 정각(1h 주기)에 정리한다.
     * RWX NFS 를 다중 replica 가 공유한다. SchedulerLock 은 shedlock 배선 시 단일 replica 실행을 보장하며,
     * 미배선 상태라도 각 정리 연산(로컬 삭제/MinIO 삭제/마커 삭제/로그 insert)이 idempotent 해
     * 다중 replica 동시 실행 시에도 데이터 손상 없이 안전하다.
     */
    @Scheduled(cron = "0 0 * * * *", zone = "Asia/Seoul")
    @SchedulerLock(
            name = "cleanupPartialRecordingLock",
            lockAtLeastFor = "30s", // 배선 시: 빨리 끝나도 최소 30초는 Lock 유지해 재진입 억제
            lockAtMostFor = "5m"    // 배선 시: NFS/MinIO I/O 여유 + replica 사망 시 Lock 자동 해제
    )
    public void cleanupPartialRecording() {
        try {
            CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();
            log.info("##########################");
            log.info("Partial Recording Cleanup :: deleted={}, skipped={}, failed={}",
                    result.deleted(), result.skipped(), result.failed());
            log.info("##########################");
        } catch (ChatForYouException e) {
            log.error("partial 녹화 정리 배치 실패: code={}, message={}",
                    e.getErrorCode().getCode(), e.getMessage());
        } catch (Exception e) {
            log.error("partial 녹화 정리 배치 중 예기치 않은 오류: {}", e.getMessage(), e);
        }
    }
}
