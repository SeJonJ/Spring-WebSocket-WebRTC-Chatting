package webChat.service.recording;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import webChat.entity.DownloadLog;
import webChat.model.record.RecordingPartialMarker;
import webChat.service.file.impl.RecordingFileService;
import webChat.service.monitoring.DownloadLogService;
import webChat.service.redis.RedisService;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.stream.Stream;

/**
 * 중단된 방 녹화의 partial 파일을 정리한다.
 * partial 마커 스캔 → age 필터 → 로컬 파일 삭제 → MinIO 방어 삭제 → 감사 로그 → 마커 삭제 순으로 오케스트레이션한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RecordingPartialCleanupService {

    private final RedisService redisService;
    private final RecordingFileService recordingFileService;
    private final DownloadLogService downloadLogService;

    @Value("${recording.partial.cleanup.age-seconds:14400}")
    private long cleanupAgeSeconds;

    /**
     * age 임계값을 넘긴 partial 녹화 파일을 정리한다.
     * 마커 1건 실패가 배치 전체를 중단시키지 않도록 마커 단위로 예외를 격리한다.
     * 각 연산(로컬 삭제/MinIO 삭제/마커 삭제/로그 insert)이 idempotent 하므로 다중 replica 가 동시에
     * 실행돼도 파일/마커 부재를 정상 흐름으로 흡수하며, 최악의 경우 감사 로그 중복 로우만 남는다.
     */
    public CleanupResult cleanupExpiredPartialRecordings() {
        List<RecordingPartialMarker> markers = redisService.getAllRecordingPartialMarkers();
        int deleted = 0;
        int skipped = 0;
        int failed = 0;
        long now = System.currentTimeMillis();

        for (RecordingPartialMarker marker : markers) {
            try {
                // markedAt 기준 age 가 임계값 미만이면 다음 회차로 미룬다(마커 TTL evict 전 재처리 기회 확보)
                if (now - marker.getMarkedAt() < cleanupAgeSeconds * 1000L) {
                    skipped++;
                    continue;
                }
                if (!isCurrentMarker(marker)) {
                    skipped++;
                    log.warn("partial 정리 스킵: 최신 마커 불일치 roomId={}, recordingId={}",
                            marker.getRoomId(), marker.getRecordingId());
                    continue;
                }
                deleteLocalRecordingDirectory(marker);
                deleteMinioObjectIfPresent(marker);
                downloadLogService.saveDownloadLog(DownloadLog.ofSystemAutoDeleted(marker));
                if (redisService.deleteRecordingPartialMarkerIfRecordingIdMatches(
                        marker.getRoomId(), marker.getRecordingId())) {
                    deleted++;
                } else {
                    skipped++;
                    log.warn("partial 마커 삭제 스킵: roomId={}, recordingId={}",
                            marker.getRoomId(), marker.getRecordingId());
                }
            } catch (Exception e) {
                failed++;
                log.error("partial 녹화 정리 실패: roomId={}, recordingId={}",
                        marker.getRoomId(), marker.getRecordingId(), e);
            }
        }
        return new CleanupResult(deleted, skipped, failed);
    }

    private boolean isCurrentMarker(RecordingPartialMarker marker) {
        RecordingPartialMarker currentMarker = redisService.getRecordingPartialMarker(marker.getRoomId());
        return currentMarker != null
                && Objects.equals(currentMarker.getRecordingId(), marker.getRecordingId());
    }

    // 로컬 PVC의 recordingId 디렉토리 삭제. roomId 디렉토리는 새 녹화와 충돌할 수 있어 삭제하지 않는다.
    private void deleteLocalRecordingDirectory(RecordingPartialMarker marker) throws IOException {
        String fileFullPath = marker.getFileFullPath();
        if (fileFullPath == null || fileFullPath.isBlank()) {
            log.warn("partial 로컬 파일 경로 없음: roomId={}", marker.getRoomId());
            return;
        }
        Path localFilePath = Path.of(fileFullPath.replace("file://", ""));
        Path recordingDirectory = localFilePath.getParent();
        if (recordingDirectory == null) {
            log.warn("partial 로컬 파일 부모 디렉토리 없음: path={}", localFilePath);
            return;
        }

        if (!Objects.equals(recordingDirectory.getFileName().toString(), marker.getRecordingId())) {
            deleteLocalFileOnly(localFilePath);
            return;
        }

        if (!Files.exists(recordingDirectory)) {
            log.warn("partial 로컬 녹화 디렉토리 부재: path={}", recordingDirectory);
            return;
        }
        deleteDirectoryRecursively(recordingDirectory);
        log.info("partial 로컬 녹화 디렉토리 삭제: path={}", recordingDirectory);
    }

    private void deleteLocalFileOnly(Path localFilePath) throws IOException {
        File localFile = localFilePath.toFile();
        if (!localFile.exists()) {
            log.warn("partial 로컬 파일 부재: path={}", localFilePath);
            return;
        }
        if (localFile.delete()) {
            log.info("partial 로컬 파일 삭제: path={}", localFilePath);
        } else {
            throw new IOException("partial 로컬 파일 삭제 실패: path=" + localFilePath);
        }
    }

    private void deleteDirectoryRecursively(Path directory) throws IOException {
        try (Stream<Path> paths = Files.walk(directory)) {
            paths.sorted(Comparator.reverseOrder())
                    .forEach(path -> {
                        try {
                            Files.deleteIfExists(path);
                        } catch (IOException e) {
                            throw new UncheckedIOException(e);
                        }
                    });
        } catch (UncheckedIOException e) {
            throw e.getCause();
        }
    }

    // MinIO 객체 삭제. partial 은 업로드 전 중단이라 보통 minioFilePath 가 비어 있어 스킵이 정상 케이스다.
    private void deleteMinioObjectIfPresent(RecordingPartialMarker marker) {
        String minioFilePath = marker.getMinioFilePath();
        if (minioFilePath == null || minioFilePath.isBlank()) {
            return;
        }
        recordingFileService.deleteFileDir(minioFilePath);
    }
}
