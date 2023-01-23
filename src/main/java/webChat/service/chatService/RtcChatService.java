package webChat.service.chatService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.kurento.client.KurentoClient;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.KurentoRoomDto;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@RequiredArgsConstructor
@Service
public class RtcChatService {

    private final KurentoClient kurento;

    // repository substitution since this is a very simple realization

    public KurentoRoomDto createChatRoom(String roomName, String roomPwd, boolean secretChk, int maxUserCnt) {
        // roomName 와 roomPwd 로 chatRoom 빌드 후 return
//        KurentoRoom room = KurentoRoom.builder()
//                .roomId(UUID.randomUUID().toString())
//                .roomName(roomName)
//                .roomPwd(roomPwd) // 채팅방 패스워드
//                .secretChk(secretChk) // 채팅방 잠금 여부
//                .userCount(0) // 채팅방 참여 인원수
//                .maxUserCnt(maxUserCnt) // 최대 인원수 제한
//                .chatType(ChatRoomDto.ChatType.RTC)
//                .build();
        KurentoRoomDto room = new KurentoRoomDto();
        String roomId = UUID.randomUUID().toString();
        room.setRoomInfo(roomId, roomName, roomPwd, secretChk, 0, maxUserCnt, ChatRoomDto.ChatType.RTC, kurento);

        // 파이프라인 생성
        room.createPipline();

        room.setUserList(new ConcurrentHashMap<String, WebSocketSession>());

        // map 에 채팅룸 아이디와 만들어진 채팅룸을 저장
        ChatRoomMap.getInstance().getChatRooms().put(room.getRoomId(), room);

        return room;
    }

}
