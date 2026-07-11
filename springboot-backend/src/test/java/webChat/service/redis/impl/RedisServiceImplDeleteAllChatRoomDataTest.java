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
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ScanOptions;

import java.nio.charset.StandardCharsets;
import java.util.Collection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class RedisServiceImplDeleteAllChatRoomDataTest {

    private static final String ROOM_ID = "room-qa-001";
    private static final String ROOM_KEY = "roomId:" + ROOM_ID;
    private static final String PARTIAL_MARKER_KEY = "room:recording:partial:" + ROOM_ID;

    @Mock
    private RedisTemplate<String, Object> masterTemplate;
    @Mock
    private RedisTemplate<String, Object> slaveTemplate;
    @Mock
    private ObjectMapper objectMapper;
    @Mock
    private RediSearchClient rediSearchClient;
    @Mock
    private RedisConnectionFactory connectionFactory;
    @Mock
    private RedisConnection connection;
    @Mock
    private Cursor<byte[]> cursor;

    private RedisServiceImpl sut;

    @BeforeEach
    void setUp() {
        sut = new RedisServiceImpl(masterTemplate, slaveTemplate, objectMapper, rediSearchClient);
    }

    @Test
    @DisplayName("deleteAllChatRoomData_roomId와partialMarker가같이매칭되어도partialMarker는삭제하지않는다")
    void deleteAllChatRoomData_preservesRecordingPartialMarker() {
        // given
        given(slaveTemplate.execute(any(RedisCallback.class))).willAnswer(invocation -> {
            RedisCallback<?> callback = invocation.getArgument(0);
            return callback.doInRedis(connection);
        });
        given(connection.scan(any(ScanOptions.class))).willReturn(cursor);
        given(cursor.hasNext()).willReturn(true, true, false);
        given(cursor.next()).willReturn(
                ROOM_KEY.getBytes(StandardCharsets.UTF_8),
                PARTIAL_MARKER_KEY.getBytes(StandardCharsets.UTF_8)
        );

        // when
        boolean result = sut.deleteAllChatRoomData(ROOM_ID);

        // then
        assertThat(result).isTrue();
        ArgumentCaptor<Collection<String>> keysCaptor = ArgumentCaptor.forClass(Collection.class);
        verify(masterTemplate).delete(keysCaptor.capture());
        assertThat(keysCaptor.getValue())
                .containsExactly(ROOM_KEY)
                .doesNotContain(PARTIAL_MARKER_KEY);
    }
}
