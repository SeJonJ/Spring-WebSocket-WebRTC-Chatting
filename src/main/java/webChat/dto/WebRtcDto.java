package webChat.dto;

/*
*  클라이언트와 주고받을 Model !!
*  SignalHandler 에서 사용
* */

import lombok.*;

@Setter
@Getter
@NoArgsConstructor
@AllArgsConstructor
@ToString
@EqualsAndHashCode // 데이터 비교를 위해 사용??
public class WebRtcDto {
    private String from;
    private String type;
    private String data;
    private Object candidate;
    private Object sdp;
}
