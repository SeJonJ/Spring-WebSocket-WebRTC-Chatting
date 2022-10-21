package webChat.dto;

/*
*  클라이언트와 주고받을 Model !!
*  SignalHandler 에서 사용
* */

import lombok.*;

/* TODO WebRTC 관련 */
@Data
@ToString
@EqualsAndHashCode // 데이터 비교를 위해 사용??
public class SignalMessageDto {
    private String type;
    private String sender;
    private String receiver;
    private Object data;
}
