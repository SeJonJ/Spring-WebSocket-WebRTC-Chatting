package webChat.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import webChat.dto.SignalMessageDto;

/* TODO WebRTC 관련 */
public class Utils {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    private Utils(){

    }

    public static SignalMessageDto getObject(String message) throws JsonProcessingException {
        return objectMapper.readValue(message, SignalMessageDto.class);
    }

    public static String getString(SignalMessageDto webRtcDto) throws JsonProcessingException {
        return objectMapper.writeValueAsString(webRtcDto);
    }
}
