package webChat.dao;

import org.springframework.stereotype.Repository;
import webChat.dto.ChatRoom;

import javax.annotation.PostConstruct;
import java.util.*;

// 추후 DB 와 연결 시 query 문으로 대체 예정
@Repository
public class ChatRepository {

    private Map<String, ChatRoom> chatRoomMap;

    @PostConstruct
    private void init() {
        chatRoomMap = new LinkedHashMap<>();
    }

    public List<ChatRoom> findAllRoom(){
        // 채팅방 생성 순서를 최근순으로 반환
        List chatRooms = new ArrayList<>(chatRoomMap.values());
        Collections.reverse(chatRooms);

        return chatRooms;
    }

    public ChatRoom findRoomById(String roomId){
        return chatRoomMap.get(roomId);
    }

    public ChatRoom createChatRoom(String roomName){
        ChatRoom chatRoom = new ChatRoom().create(roomName);
        chatRoomMap.put(chatRoom.getRoomId(), chatRoom);

        return chatRoom;
    }
}
