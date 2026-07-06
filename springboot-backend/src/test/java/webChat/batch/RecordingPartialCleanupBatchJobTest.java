package webChat.batch;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import webChat.exception.ChatForYouException;
import webChat.exception.ErrorCode;
import webChat.service.recording.CleanupResult;
import webChat.service.recording.RecordingPartialCleanupService;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.willThrow;
import static org.mockito.Mockito.verify;

/**
 * RecordingPartialCleanupBatchJob 단위 테스트 — 배치 래퍼가 서비스 예외를 삼키고
 * 호출자(스케줄러)에게 전파하지 않는지 검증한다(RoomBatchJob 패턴 준수 확인).
 */
@ExtendWith(MockitoExtension.class)
class RecordingPartialCleanupBatchJobTest {

    @Mock
    private RecordingPartialCleanupService recordingPartialCleanupService;

    @InjectMocks
    private RecordingPartialCleanupBatchJob recordingPartialCleanupBatchJob;

    // 배치 로깅 검증용 카운트일 뿐 도메인 의미는 없어 로컬 헬퍼로 매직 리터럴을 분리한다.
    private CleanupResult normalCleanupResult() {
        return new CleanupResult(2, 1, 0);
    }

    @Test
    @DisplayName("cleanupPartialRecording_서비스정상반환_예외없이카운트로깅하고종료")
    void cleanupPartialRecording_serviceSucceeds_completesWithoutException() {
        // given
        given(recordingPartialCleanupService.cleanupExpiredPartialRecordings())
                .willReturn(normalCleanupResult());

        // when & then
        // 예외 없이 정상 반환되고 서비스가 정확히 1회 호출된다
        assertThatCode(() -> recordingPartialCleanupBatchJob.cleanupPartialRecording())
                .doesNotThrowAnyException();
        verify(recordingPartialCleanupService).cleanupExpiredPartialRecordings();
    }

    @Test
    @DisplayName("cleanupPartialRecording_서비스가ChatForYouException던짐_배치가삼키고전파하지않음")
    void cleanupPartialRecording_serviceThrowsChatForYouException_swallowsAndDoesNotPropagate() {
        // given
        willThrow(new ChatForYouException(ErrorCode.INTERNAL_SERVER_ERROR))
                .given(recordingPartialCleanupService).cleanupExpiredPartialRecordings();

        // when & then
        // 배치 메서드가 예외를 로깅만 하고 호출자에게 전파하지 않는다
        assertThatCode(() -> recordingPartialCleanupBatchJob.cleanupPartialRecording())
                .doesNotThrowAnyException();
    }

    @Test
    @DisplayName("cleanupPartialRecording_서비스가일반Exception던짐_배치가삼키고전파하지않음")
    void cleanupPartialRecording_serviceThrowsGenericException_swallowsAndDoesNotPropagate() {
        // given
        willThrow(new RuntimeException("예기치 않은 오류"))
                .given(recordingPartialCleanupService).cleanupExpiredPartialRecordings();

        // when & then
        assertThatCode(() -> recordingPartialCleanupBatchJob.cleanupPartialRecording())
                .doesNotThrowAnyException();
    }
}
