package webChat.dto;

import lombok.Builder;
import lombok.Data;

import java.util.UUID;


// pub/sub 를 사용하면 구독자 관리가 알아서 된다!!
// 따라서 따로 세션 관리를 하는 코드를 작성할 필도 없고,
// 메시지를 다른 세션의 클라이언트에게 발송하는 것도 구현 필요가 없다!
@Data
public class ChatRoom {
    private String roomId; // 채팅방 아이디
    private String roomName; // 채팅방 이름

    public ChatRoom create(String roomName){
        ChatRoom chatRoom = new ChatRoom();
        chatRoom.roomId = UUID.randomUUID().toString();
        chatRoom.roomName = roomName;

        return chatRoom;
    }

}
