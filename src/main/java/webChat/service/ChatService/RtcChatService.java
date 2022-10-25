package webChat.service.ChatService;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;
import webChat.dto.ChatRoomDto;

import javax.annotation.PostConstruct;
import java.util.*;

@Service
@RequiredArgsConstructor
public class RtcChatService {

//    private final ChatServiceMain chatServiceMain;

    public ChatRoomDto createChatRoom(Map<String, ChatRoomDto> chatRoomMap, String roomName, String roomPwd, boolean secretChk, int maxUserCnt) {
        // roomName 와 roomPwd 로 chatRoom 빌드 후 return
        ChatRoomDto room = ChatRoomDto.builder()
                .roomId(UUID.randomUUID().toString())
                .roomName(roomName)
                .roomPwd(roomPwd) // 채팅방 패스워드
                .secretChk(secretChk) // 채팅방 잠금 여부
                .userCount(0) // 채팅방 참여 인원수
                .maxUserCnt(maxUserCnt) // 최대 인원수 제한
                .build();

        room.setUserList(new HashMap<String, WebSocketSession>());

        // msg 타입이면 ChatType.MSG
        room.setChatType(ChatRoomDto.ChatType.RTC);

        // map 에 채팅룸 아이디와 만들어진 채팅룸을 저장
        chatRoomMap.put(room.getRoomId(), room);

        return room;
    }
//
//    @Override
//    public boolean confirmPwd(String roomId, String roomPwd) {
//        return super.confirmPwd(roomId, roomPwd);
//    }
//
//    @Override
//    public void plusUserCnt(String roomId) {
//        super.plusUserCnt(roomId);
//    }
//
//    @Override
//    public void minusUserCnt(String roomId) {
//        super.minusUserCnt(roomId);
//    }
//
//    @Override
//    public boolean chkRoomUserCnt(String roomId) {
//        return super.chkRoomUserCnt(roomId);
//    }


}
