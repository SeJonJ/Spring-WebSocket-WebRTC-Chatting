package webChat.dto;

import lombok.*;


@Data
@AllArgsConstructor
@NoArgsConstructor
public class WebSocketMessage {
    private String from;
    private String type;
    private String roomId;
    private Object candidate;
    private Object sdp;


}
