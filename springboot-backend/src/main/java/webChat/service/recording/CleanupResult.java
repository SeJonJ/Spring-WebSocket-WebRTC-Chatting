package webChat.service.recording;

/**
 * partial 녹화 정리 배치 1회 실행 결과 카운트. 로그·테스트 검증용.
 */
public record CleanupResult(int deleted, int skipped, int failed) {
}
