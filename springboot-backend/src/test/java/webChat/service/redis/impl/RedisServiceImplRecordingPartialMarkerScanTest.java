package webChat.service.redis.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.dengliming.redismodule.redisearch.client.RediSearchClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.ValueOperations;
import webChat.model.record.RecordingPartialMarker;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

/**
 * RedisServiceImpl.getAllRecordingPartialMarkers() SCAN 조회 테스트.
 * 기존 RedisServiceImplRecordingPartialMarkerTest 와 동일하게 RedisTemplate/Cursor 를 모킹하는
 * 순수 단위 테스트 레이어(임베디드 Redis 미사용)를 따른다. save 한 마커들이 SCAN 으로 전부
 * 조회되는지, 마커 0건일 때 빈 리스트를 반환하는지 검증한다.
 */
@ExtendWith(MockitoExtension.class)
class RedisServiceImplRecordingPartialMarkerScanTest {

    private static final String KEY_PREFIX = "room:recording:partial:";

    @Mock
    private RedisTemplate<String, Object> masterTemplate;

    @Mock
    private RedisTemplate<String, Object> slaveTemplate;

    @Mock
    private ObjectMapper objectMapper;

    @Mock
    private RediSearchClient rediSearchClient;

    @Mock
    private ValueOperations<String, Object> valueOperations;

    @Mock
    private RedisConnection connection;

    @Mock
    private Cursor<byte[]> cursor;

    private RedisServiceImpl sut;

    @BeforeEach
    void setUp() {
        sut = new RedisServiceImpl(masterTemplate, slaveTemplate, objectMapper, rediSearchClient);
        given(slaveTemplate.execute(any(RedisCallback.class))).willAnswer(invocation -> {
            RedisCallback<?> callback = invocation.getArgument(0);
            return callback.doInRedis(connection);
        });
        given(connection.scan(any(ScanOptions.class))).willReturn(cursor);
    }

    private RecordingPartialMarker marker(String roomId, String recordingId) {
        return RecordingPartialMarker.builder()
                .roomId(roomId)
                .recordingId(recordingId)
                .recordingUserId("user-1")
                .fileName("rec.mp4")
                .filePath(roomId + "/" + recordingId + "/rec.mp4")
                .fileFullPath("/data/" + roomId + "/" + recordingId + "/rec.mp4")
                .minioFilePath(null)
                .startAt(1_000_000L)
                .markedAt(System.currentTimeMillis())
                .notified(false)
                .build();
    }

    @Test
    @DisplayName("getAllRecordingPartialMarkers_저장된마커2건_SCAN으로전부조회하고필드보존확인")
    void getAllRecordingPartialMarkers_savedTwoMarkers_scansAllAndPreservesFields() {
        // given
        // SCAN 이 키 2건을 반환하고, 각 키에 대해 master get 이 저장된 마커를 반환(round-trip)
        RecordingPartialMarker markerA = marker("room-a", "rec-a");
        RecordingPartialMarker markerB = marker("room-b", "rec-b");
        String keyA = KEY_PREFIX + "room-a";
        String keyB = KEY_PREFIX + "room-b";

        given(cursor.hasNext()).willReturn(true, true, false);
        given(cursor.next()).willReturn(keyA.getBytes(), keyB.getBytes());

        given(masterTemplate.opsForValue()).willReturn(valueOperations);
        given(valueOperations.get(keyA)).willReturn(markerA);
        given(valueOperations.get(keyB)).willReturn(markerB);

        // when
        List<RecordingPartialMarker> result = sut.getAllRecordingPartialMarkers();

        // then
        // 저장된 2건이 모두 조회되고, 필드가 그대로 보존된다
        assertThat(result).hasSize(2);
        assertThat(result).extracting(RecordingPartialMarker::getRoomId)
                .containsExactlyInAnyOrder("room-a", "room-b");
        assertThat(result).extracting(RecordingPartialMarker::getRecordingId)
                .containsExactlyInAnyOrder("rec-a", "rec-b");
        assertThat(result).extracting(RecordingPartialMarker::getFileName)
                .containsOnly("rec.mp4");
    }

    @Test
    @DisplayName("getAllRecordingPartialMarkers_마커0건_빈리스트반환")
    void getAllRecordingPartialMarkers_noMarkers_returnsEmptyList() {
        // given
        // SCAN 이 키를 하나도 반환하지 않음
        given(cursor.hasNext()).willReturn(false);

        // when
        List<RecordingPartialMarker> result = sut.getAllRecordingPartialMarkers();

        // then
        assertThat(result).isEmpty();
    }

    @Test
    @DisplayName("getAllRecordingPartialMarkers_scan패턴은room콜론recording콜론partial콜론와일드카드이다")
    void getAllRecordingPartialMarkers_usesRecordingPartialPrefixPattern() {
        // given
        given(cursor.hasNext()).willReturn(false);

        // when
        sut.getAllRecordingPartialMarkers();

        // then
        // SCAN 이 room:recording:partial:* 패턴으로 호출된다(기존 마커 키 prefix 와 일관)
        ArgumentCaptor<ScanOptions> optionsCaptor = ArgumentCaptor.forClass(ScanOptions.class);
        org.mockito.Mockito.verify(connection).scan(optionsCaptor.capture());
        assertThat(optionsCaptor.getValue().getPattern()).isEqualTo(KEY_PREFIX + "*");
    }

    @Test
    @DisplayName("getAllRecordingPartialMarkers_값이RecordingPartialMarker타입이아니면방어적으로제외한다")
    void getAllRecordingPartialMarkers_valueNotMarkerType_isDefensivelyExcluded() {
        // given
        // 키는 스캔되지만 master get 결과가 null(TTL 만료 등 race)
        String key = KEY_PREFIX + "room-race";
        given(cursor.hasNext()).willReturn(true, false);
        given(cursor.next()).willReturn(key.getBytes());
        given(masterTemplate.opsForValue()).willReturn(valueOperations);
        given(valueOperations.get(key)).willReturn(null);

        // when
        List<RecordingPartialMarker> result = sut.getAllRecordingPartialMarkers();

        // then
        // null/타입불일치 값은 결과에서 방어적으로 제외된다
        assertThat(result).isEmpty();
    }
}
