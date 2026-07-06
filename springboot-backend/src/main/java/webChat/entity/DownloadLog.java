package webChat.entity;

import jakarta.persistence.*;
import lombok.*;
import webChat.model.record.RecordingPartialMarker;

/**
 * 다운로드 히스토리 로그
 * 6개월 단위로 삭제
 */
@Entity
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Table(name = "download_log", indexes = {
        // 1. 데이터 파기 및 기간별 조회를 위한 인덱스
        @Index(name = "idx_created_at", columnList = "createdAt"),

        // 2. 특정 사용자의 활동 추적을 위한 복합 인덱스
        @Index(name = "idx_user_search", columnList = "userIdx, targetType, createdAt"),

        // 3. 특정 리소스(파일/녹화본)의 다운로드 이력 확인을 위한 인덱스
        @Index(name = "idx_target_search", columnList = "targetType, targetId")
})
public class DownloadLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private long idx;

    private Long userIdx;

    private String email;

    private String roomId;

    @Enumerated(EnumType.STRING)
    private DownloadType targetType;

    @Getter
    public enum DownloadType {
        RECORDING, FILE;
    }

    // type 에 따른 target 의 id
    // recording 일 때는 recordId, file 일때는 fileId
    private String targetId;

    private String fileName;

    private String filePath;

    private String ipAddress;

    @Column(columnDefinition = "TEXT")
    private String userAgent;

    @Enumerated(EnumType.STRING)
    private DownloadStatus status;

    @Getter
    public enum DownloadStatus {
        SUCCESS, FAIL, PENDING, SYSTEM_AUTO_DELETED
    }

    @Column(updatable = false)
    private long createdAt;

    // 저장 직전 시간 자동 입력 (ms 단위)
    @PrePersist
    public void prePersist() {
        this.createdAt = System.currentTimeMillis();
    }

    public static DownloadLog of(Long userIdx, String email, String roomId,
                                 DownloadType type, String filePath, String fileName,
                                 String ipAddress, String userAgent, DownloadStatus status) {
        String[] parts = filePath.split("/");
        String targetId = parts.length >= 2 ? parts[1] : "unknown";
        return DownloadLog.builder()
                .userIdx(userIdx)
                .email(email)
                .roomId(roomId)
                .targetType(type)
                .targetId(targetId)
                .fileName(fileName)
                .filePath(filePath)
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .status(status)
                .build();
    }

    /**
     * 시스템 배치가 partial 녹화 파일을 자동 삭제한 사실을 기록하는 감사 로그를 만든다.
     * of() 는 filePath.split 로 targetId 를 파생하고 filePath null 시 NPE 라, 마커의 recordingId 를 targetId 로 직접 사용한다.
     */
    public static DownloadLog ofSystemAutoDeleted(RecordingPartialMarker marker) {
        return DownloadLog.builder()
                .userIdx(null)
                .email(marker.getRecordingUserId())
                .roomId(marker.getRoomId())
                .targetType(DownloadType.RECORDING)
                .targetId(marker.getRecordingId())
                .fileName(marker.getFileName())
                .filePath(marker.getFilePath())
                .ipAddress(null)
                .userAgent(null)
                .status(DownloadStatus.SYSTEM_AUTO_DELETED)
                .build();
    }
}
