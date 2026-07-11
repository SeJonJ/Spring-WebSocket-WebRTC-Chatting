package webChat.service.recording;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import webChat.entity.DownloadLog;
import webChat.model.record.RecordingPartialMarker;
import webChat.service.file.impl.RecordingFileService;
import webChat.service.monitoring.DownloadLogService;
import webChat.service.redis.RedisService;

import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

/**
 * RecordingPartialCleanupService 단위 테스트 — 구현 메서드의 정상 케이스 + 단순 예외.
 * 경계값/개별 실패 격리/동시성/통합은 QA 전문가 담당.
 */
@ExtendWith(MockitoExtension.class)
class RecordingPartialCleanupServiceTest {

    private static final long AGE_SECONDS = 14400L;

    @Mock
    private RedisService redisService;

    @Mock
    private RecordingFileService recordingFileService;

    @Mock
    private DownloadLogService downloadLogService;

    @InjectMocks
    private RecordingPartialCleanupService recordingPartialCleanupService;

    private void setAgeThreshold() {
        ReflectionTestUtils.setField(recordingPartialCleanupService, "cleanupAgeSeconds", AGE_SECONDS);
    }

    private RecordingPartialMarker markerWith(long markedAt, String fileFullPath, String minioFilePath) {
        return RecordingPartialMarker.builder()
                .roomId("room-1")
                .recordingId("rec-1")
                .recordingUserId("user-1")
                .fileName("rec.mp4")
                .filePath("room-1/rec-1/rec.mp4")
                .fileFullPath(fileFullPath)
                .minioFilePath(minioFilePath)
                .markedAt(markedAt)
                .build();
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_임계값초과마커_파일삭제및로그및마커삭제")
    void cleanupExpiredPartialRecordings_expiredMarker_deletesFileLogsAndRemovesMarker(@TempDir Path tempDir) throws IOException {
        // given
        setAgeThreshold();
        File partialFile = tempDir.resolve("rec.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        long expiredMarkedAt = System.currentTimeMillis() - (AGE_SECONDS * 1000L) - 1000L;
        RecordingPartialMarker marker = markerWith(expiredMarkedAt, partialFile.getAbsolutePath(), null);
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-1")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-1", "rec-1"))
                .willReturn(true);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.deleted()).isEqualTo(1);
        assertThat(result.skipped()).isZero();
        assertThat(result.failed()).isZero();
        assertThat(partialFile).doesNotExist();

        ArgumentCaptor<DownloadLog> logCaptor = ArgumentCaptor.forClass(DownloadLog.class);
        verify(downloadLogService).saveDownloadLog(logCaptor.capture());
        DownloadLog savedLog = logCaptor.getValue();
        assertThat(savedLog.getStatus()).isEqualTo(DownloadLog.DownloadStatus.SYSTEM_AUTO_DELETED);
        assertThat(savedLog.getTargetId()).isEqualTo("rec-1");
        assertThat(savedLog.getRoomId()).isEqualTo("room-1");
        assertThat(savedLog.getFileName()).isEqualTo("rec.mp4");

        verify(redisService).deleteRecordingPartialMarkerIfRecordingIdMatches("room-1", "rec-1");
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_마커조건부삭제실패_스킵으로집계")
    void cleanupExpiredPartialRecordings_conditionalMarkerDeleteFails_countsAsSkipped(@TempDir Path tempDir) throws IOException {
        // given
        setAgeThreshold();
        File partialFile = tempDir.resolve("rec.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        long expiredMarkedAt = System.currentTimeMillis() - (AGE_SECONDS * 1000L) - 1000L;
        RecordingPartialMarker marker = markerWith(expiredMarkedAt, partialFile.getAbsolutePath(), null);
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-1")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-1", "rec-1"))
                .willReturn(false);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.deleted()).isZero();
        assertThat(result.skipped()).isEqualTo(1);
        assertThat(result.failed()).isZero();
        assertThat(partialFile).doesNotExist();
        verify(downloadLogService).saveDownloadLog(org.mockito.ArgumentMatchers.any());
        verify(redisService).deleteRecordingPartialMarkerIfRecordingIdMatches("room-1", "rec-1");
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_임계값미만마커_스킵")
    void cleanupExpiredPartialRecordings_notExpiredMarker_skips() {
        // given
        setAgeThreshold();
        long freshMarkedAt = System.currentTimeMillis();
        RecordingPartialMarker marker = markerWith(freshMarkedAt, "/tmp/rec.mp4", null);
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.skipped()).isEqualTo(1);
        assertThat(result.deleted()).isZero();
        assertThat(result.failed()).isZero();
        verify(downloadLogService, never()).saveDownloadLog(org.mockito.ArgumentMatchers.any());
        verify(redisService, never()).deleteRecordingPartialMarkerIfRecordingIdMatches(
                org.mockito.ArgumentMatchers.anyString(), org.mockito.ArgumentMatchers.anyString());
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_마커없음_카운트0반환")
    void cleanupExpiredPartialRecordings_noMarkers_returnsZeroCounts() {
        // given
        setAgeThreshold();
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of());

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.deleted()).isZero();
        assertThat(result.skipped()).isZero();
        assertThat(result.failed()).isZero();
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_minioFilePath존재_MinIO객체삭제호출")
    void cleanupExpiredPartialRecordings_minioPathPresent_callsMinioDelete(@TempDir Path tempDir) throws IOException {
        // given
        setAgeThreshold();
        File partialFile = tempDir.resolve("rec.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        long expiredMarkedAt = System.currentTimeMillis() - (AGE_SECONDS * 1000L) - 1000L;
        String minioFilePath = "room-1/rec-1/rec.mp4";
        RecordingPartialMarker marker = markerWith(expiredMarkedAt, partialFile.getAbsolutePath(), minioFilePath);
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-1")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-1", "rec-1"))
                .willReturn(true);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.deleted()).isEqualTo(1);
        verify(recordingFileService).deleteFileDir(eq(minioFilePath));
    }
}
