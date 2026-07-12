package webChat.entity;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import webChat.model.record.RecordingPartialMarker;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * DownloadLog.ofSystemAutoDeleted 필드 매핑 검증.
 * 시스템 배치가 partial 녹화 파일을 자동 삭제했을 때 감사 로그 필드가 마커 정보와
 * 정확히 매핑되는지(특히 targetId=recordingId, userIdx=null) 확인한다.
 */
class DownloadLogTest {

    private RecordingPartialMarker marker() {
        return RecordingPartialMarker.builder()
                .roomId("room-1")
                .recordingId("rec-1")
                .recordingUserId("user-1@test.com")
                .recordingNickName("테스터")
                .fileName("rec.mp4")
                .filePath("room-1/rec-1/rec.mp4")
                .fileFullPath("file:///data/room-1/rec-1/rec.mp4")
                .minioFilePath(null)
                .startAt(1_000_000L)
                .markedAt(System.currentTimeMillis())
                .notified(false)
                .build();
    }

    @Test
    @DisplayName("ofSystemAutoDeleted_마커전달_status는SYSTEM_AUTO_DELETED이고targetType은RECORDING이다")
    void ofSystemAutoDeleted_givenMarker_statusIsSystemAutoDeletedAndTargetTypeIsRecording() {
        // given
        RecordingPartialMarker marker = marker();

        // when
        DownloadLog result = DownloadLog.ofSystemAutoDeleted(marker);

        // then
        assertThat(result.getStatus()).isEqualTo(DownloadLog.DownloadStatus.SYSTEM_AUTO_DELETED);
        assertThat(result.getTargetType()).isEqualTo(DownloadLog.DownloadType.RECORDING);
    }

    @Test
    @DisplayName("ofSystemAutoDeleted_마커전달_targetId는recordingId를직접사용한다")
    void ofSystemAutoDeleted_givenMarker_targetIdUsesRecordingIdDirectly() {
        // given
        RecordingPartialMarker marker = marker();

        // when
        DownloadLog result = DownloadLog.ofSystemAutoDeleted(marker);

        // then
        // of() 의 filePath.split 파생 방식이 아니라 recordingId 를 그대로 사용한다
        assertThat(result.getTargetId()).isEqualTo("rec-1");
    }

    @Test
    @DisplayName("ofSystemAutoDeleted_마커전달_roomId및fileName및filePath가마커값으로매핑된다")
    void ofSystemAutoDeleted_givenMarker_roomIdFileNameFilePathMappedFromMarker() {
        // given
        RecordingPartialMarker marker = marker();

        // when
        DownloadLog result = DownloadLog.ofSystemAutoDeleted(marker);

        // then
        assertThat(result.getRoomId()).isEqualTo("room-1");
        assertThat(result.getFileName()).isEqualTo("rec.mp4");
        assertThat(result.getFilePath()).isEqualTo("room-1/rec-1/rec.mp4");
    }

    @Test
    @DisplayName("ofSystemAutoDeleted_마커전달_userIdx는null이고ipAddress및userAgent도null이다")
    void ofSystemAutoDeleted_givenMarker_userIdxAndIpAddressAndUserAgentAreNull() {
        // given
        RecordingPartialMarker marker = marker();

        // when
        DownloadLog result = DownloadLog.ofSystemAutoDeleted(marker);

        // then
        // 마커에 Long userIdx 가 없고, 시스템 작업이라 ip/agent 도 없다
        assertThat(result.getUserIdx()).isNull();
        assertThat(result.getIpAddress()).isNull();
        assertThat(result.getUserAgent()).isNull();
    }

    @Test
    @DisplayName("ofSystemAutoDeleted_마커전달_email은recordingUserId로매핑된다")
    void ofSystemAutoDeleted_givenMarker_emailMappedFromRecordingUserId() {
        // given
        RecordingPartialMarker marker = marker();

        // when
        DownloadLog result = DownloadLog.ofSystemAutoDeleted(marker);

        // then
        assertThat(result.getEmail()).isEqualTo("user-1@test.com");
    }
}
