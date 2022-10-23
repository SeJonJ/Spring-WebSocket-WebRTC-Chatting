package webChat.dto;

import com.sun.istack.NotNull;
import lombok.*;
import org.springframework.web.socket.WebSocketSession;

import java.util.HashMap;
import java.util.Map;


// Stomp 를 통해 pub/sub 를 사용하면 구독자 관리가 알아서 된다!!
// 따라서 따로 세션 관리를 하는 코드를 작성할 필도 없고,
// 메시지를 다른 세션의 클라이언트에게 발송하는 것도 구현 필요가 없다!
@Data
@Builder
@EqualsAndHashCode
@Getter
@Setter
public class ChatRoomDto {
    @NotNull
    private String roomId; // 채팅방 아이디
    private String roomName; // 채팅방 이름 
    private int userCount; // 채팅방 인원수
    private int maxUserCnt; // 채팅방 최대 인원 제한

    private String roomPwd; // 채팅방 삭제시 필요한 pwd
    private boolean secretChk; // 채팅방 잠금 여부

    // TODO 여기를 어떻게 고칠 건지 생각해볼것!!
    // 클래스를 따로 나눌지 아니면 하나로 하면서 할지 고민해야함
    private Map<String, String> userList = new HashMap<>();

//    // 화상 채팅을 위한 WebSocket 와 String 연결
//    private Map<String, WebSocketSession> clients = new HashMap<>();

}
