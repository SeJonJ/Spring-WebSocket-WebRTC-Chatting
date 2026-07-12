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
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.willThrow;
import static org.mockito.Mockito.verify;

/**
 * RecordingPartialCleanupService QA 보강 테스트 — 백엔드 단위 테스트(RecordingPartialCleanupServiceTest)가
 * 다루지 않는 경계/방어/개별 실패 격리 시나리오(S4~S6)를 검증한다.
 */
@ExtendWith(MockitoExtension.class)
class RecordingPartialCleanupServiceQaTest {

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

    private long expiredMarkedAt() {
        return System.currentTimeMillis() - (AGE_SECONDS * 1000L) - 1000L;
    }

    private RecordingPartialMarker.RecordingPartialMarkerBuilder expiredMarkerBuilder(String roomId) {
        return RecordingPartialMarker.builder()
                .roomId(roomId)
                .recordingId("rec-" + roomId)
                .recordingUserId("user-1")
                .fileName("rec.mp4")
                .filePath(roomId + "/rec-" + roomId + "/rec.mp4")
                .minioFilePath(null)
                .markedAt(expiredMarkedAt());
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_S4_로컬파일이미부재_예외없이로그기록및마커삭제진행")
    void cleanupExpiredPartialRecordings_localFileAlreadyAbsent_proceedsWithoutException(@TempDir Path tempDir) {
        // given
        // fileFullPath 가 가리키는 파일을 생성하지 않아 부재 상태를 재현
        setUpService();
        File missingFile = tempDir.resolve("missing-rec.mp4").toFile();
        assertThat(missingFile).doesNotExist();

        RecordingPartialMarker marker = expiredMarkerBuilder("room-s4")
                .fileFullPath(missingFile.getAbsolutePath())
                .build();
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-s4")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-s4", "rec-room-s4"))
                .willReturn(true);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        // 파일 부재가 예외로 이어지지 않고 warn 후 정상 흐름(deleted 집계)으로 진행된다
        assertThat(result.deleted()).isEqualTo(1);
        assertThat(result.failed()).isZero();
        verify(downloadLogService).saveDownloadLog(any());
        verify(redisService).deleteRecordingPartialMarkerIfRecordingIdMatches("room-s4", "rec-room-s4");
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_S5_fileUri프리픽스_프리픽스제거된경로로파일삭제")
    void cleanupExpiredPartialRecordings_fileUriPrefix_deletesWithStrippedPath(@TempDir Path tempDir) throws Exception {
        // given
        // fileFullPath = "file://" + 실제 임시파일 절대경로
        setUpService();
        Path recordingDirectory = tempDir.resolve("room-s5").resolve("rec-room-s5");
        Files.createDirectories(recordingDirectory);
        File partialFile = recordingDirectory.resolve("rec-uri.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        String fileUriPath = "file://" + partialFile.getAbsolutePath();
        RecordingPartialMarker marker = expiredMarkerBuilder("room-s5")
                .fileFullPath(fileUriPath)
                .build();
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(marker));
        given(redisService.getRecordingPartialMarker("room-s5")).willReturn(marker);
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches("room-s5", "rec-room-s5"))
                .willReturn(true);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        // file:// 프리픽스가 제거된 실제 경로의 recordingId 디렉토리가 삭제된다
        assertThat(result.deleted()).isEqualTo(1);
        assertThat(partialFile).doesNotExist();
        assertThat(recordingDirectory).doesNotExist();
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_S6_1번째마커에서만실패_2번째마커deleted_배치중단없음")
    void cleanupExpiredPartialRecordings_onlyFirstMarkerThrows_secondMarkerDeletedNormally(@TempDir Path tempDir) {
        // given
        // 마커 2건. 1번째 roomId 에 대해서만 deleteRecordingPartialMarker 가 예외를 던지도록 설정
        setUpService();
        RecordingPartialMarker firstMarker = expiredMarkerBuilder("room-fail-2")
                .fileFullPath(null)
                .build();
        RecordingPartialMarker secondMarker = expiredMarkerBuilder("room-ok-2")
                .fileFullPath(null)
                .build();
        given(redisService.getAllRecordingPartialMarkers())
                .willReturn(List.of(firstMarker, secondMarker));
        given(redisService.getRecordingPartialMarker("room-fail-2")).willReturn(firstMarker);
        given(redisService.getRecordingPartialMarker("room-ok-2")).willReturn(secondMarker);

        willThrow(new RuntimeException("Redis 삭제 실패"))
                .given(redisService).deleteRecordingPartialMarkerIfRecordingIdMatches(
                        eq("room-fail-2"), eq("rec-room-fail-2"));
        given(redisService.deleteRecordingPartialMarkerIfRecordingIdMatches(
                "room-ok-2", "rec-room-ok-2")).willReturn(true);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        // 1번째 failed 집계 + 2번째는 정상 deleted, 배치 전체가 중단되지 않는다
        assertThat(result.failed()).isEqualTo(1);
        assertThat(result.deleted()).isEqualTo(1);
        assertThat(result.skipped()).isZero();
        verify(redisService).deleteRecordingPartialMarkerIfRecordingIdMatches("room-ok-2", "rec-room-ok-2");
        verify(downloadLogService, org.mockito.Mockito.times(2)).saveDownloadLog(any());
    }

    @Test
    @DisplayName("cleanupExpiredPartialRecordings_TOCTOU_새마커가덮어써진경우_파일삭제와로그없이스킵")
    void cleanupExpiredPartialRecordings_markerReplacedBeforeDelete_skipsWithoutFileDeleteOrLog(@TempDir Path tempDir)
            throws Exception {
        // given
        setUpService();
        File partialFile = tempDir.resolve("old-rec.mp4").toFile();
        assertThat(partialFile.createNewFile()).isTrue();

        RecordingPartialMarker oldMarker = expiredMarkerBuilder("room-race")
                .recordingId("rec-old")
                .fileFullPath(partialFile.getAbsolutePath())
                .build();
        RecordingPartialMarker newMarker = expiredMarkerBuilder("room-race")
                .recordingId("rec-new")
                .fileFullPath(tempDir.resolve("new-rec.mp4").toString())
                .build();
        given(redisService.getAllRecordingPartialMarkers()).willReturn(List.of(oldMarker));
        given(redisService.getRecordingPartialMarker("room-race")).willReturn(newMarker);

        // when
        CleanupResult result = recordingPartialCleanupService.cleanupExpiredPartialRecordings();

        // then
        assertThat(result.deleted()).isZero();
        assertThat(result.skipped()).isEqualTo(1);
        assertThat(result.failed()).isZero();
        assertThat(partialFile).exists();
        org.mockito.Mockito.verify(downloadLogService, org.mockito.Mockito.never()).saveDownloadLog(any());
        org.mockito.Mockito.verify(redisService, org.mockito.Mockito.never())
                .deleteRecordingPartialMarkerIfRecordingIdMatches(any(), any());
    }
}
