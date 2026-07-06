package webChat.service.recording;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import webChat.model.record.RecordingPartialMarker;
import webChat.service.file.impl.RecordingFileService;
import webChat.service.monitoring.DownloadLogService;
import webChat.service.redis.RedisService;

import java.io.File;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * S8 — shedlock 이 이 저장소에서 no-op(LockProvider Bean 부재, 선재 결함)임을 전제로,
 * 3 replica 가 동일 마커를 동시에 처리하는 상황을 "동일 마커에 대한 cleanup 2회 연속 실행"으로
 * 시뮬레이션한다. 두 replica 가 락 없이 동일 마커를 읽고(getAllRecordingPartialMarkers 가
 * 두 번 모두 같은 마커를 반환) 각자 정리 로직을 수행하는 시나리오를 재현해, 데이터 손상/크래시
 * 없이 두 번째 실행이 파일/마커 부재를 정상 흡수하는지, 그리고 유일한 부작용이
 * SYSTEM_AUTO_DELETED 감사 로그 중복 insert 뿐인지 검증한다.
 */
@ExtendWith(MockitoExtension.class)
class RecordingPartialCleanupIdempotencyTest {

    private static final long AGE_SECONDS = 14400L;

    @Mock
    private RedisService redisService;

    @Mock
    private RecordingFileService recordingFileService;

    @Mock
    private DownloadLogService downloadLogService;

    private RecordingPartialCleanupService recordingPartialCleanupService;

    private void setUpService() {
        recordingPartialCleanupService = new RecordingPartialCleanupService(
                redisService, recordingFileService, downloadLogService);
        ReflectionTestUtils.setField(recordingPartialCleanupService, "cleanupAgeSeconds", AGE_SECONDS);
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_동일마커를2회연속실행_두번째실행은파일마커부재를정상흡수하고크래시없음")
    void cleanupExpiredPartialRecordings_sameMarkerProcessedTwice_secondRunAbsorbsAbsenceWithoutCrash(
            @TempDir Path tempDir) throws Exception {
        // given
        // 두 replica 가 shedlock 없이 동일 마커를 동시에 읽었다고 가정 —
        // getAllRecordingPartialMarkers() 가 두 번의 배치 실행 모두에서 동일 마커를 반환한다.
        setUpService();
        File partialFile = tempDir.resolve("rec.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        long expiredMarkedAt = System.currentTimeMillis() - (AGE_SECONDS * 1000L) - 1000L;
        RecordingPartialMarker marker = RecordingPartialMarker.builder()
                .roomId("room-race")
                .recordingId("rec-race")
                .recordingUserId("user-1")
                .fileName("rec.mp4")
                .filePath("room-race/rec-race/rec.mp4")
                .fileFullPath(partialFile.getAbsolutePath())
                .minioFilePath(null)
                .markedAt(expiredMarkedAt)
                .build();

        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-race")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-race", "rec-race"))
                .willReturn(true);

        // when
        // replica A 실행 — 파일이 실제로 삭제되고 마커 삭제/로그 insert 가 호출된다
        CleanupResult firstRun = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        // 1차 실행은 정상 deleted, 파일이 실제로 사라짐
        assertThat(firstRun.deleted()).isEqualTo(1);
        assertThat(firstRun.failed()).isZero();
        assertThat(partialFile).doesNotExist();

        // when
        // replica B 실행(동일 마커, 파일은 이미 A가 삭제함) — 크래시 없이 정상 흡수돼야 한다
        assertThatCode(() -> {
            CleanupResult secondRun = recordingPartialCleanupService.cleanupExpiredPartialRecordings();
            // 2차 실행도 예외 없이 deleted 로 집계된다(파일 부재 = 정상 흐름, Redis DEL 도 부재 키에 no-op)
            assertThat(secondRun.deleted()).isEqualTo(1);
            assertThat(secondRun.failed()).isZero();
        }).doesNotThrowAnyException();

        // then
        // 유일한 부작용은 SYSTEM_AUTO_DELETED 감사 로그 중복 insert(2회) 뿐이다.
        // MinIO/로컬 파일 삭제는 idempotent(부재에도 무해)하고, 실제 파일 삭제는 1회만 일어났다.
        verify(downloadLogService, times(2)).saveDownloadLog(any());
        verify(redisService, times(2))
                .deleteRecordingPartialMarkerIfRecordingIdMatches("room-race", "rec-race");
    }
}
