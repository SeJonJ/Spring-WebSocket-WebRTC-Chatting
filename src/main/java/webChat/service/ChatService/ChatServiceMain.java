package webChat.service.ChatService;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import org.springframework.stereotype.Service;
import webChat.dto.ChatRoomDto;

import javax.annotation.PostConstruct;
import java.util.*;


@Service
@Getter
@Setter
@RequiredArgsConstructor
public class ChatServiceMain {

    private final MsgChatService msgChatService;
    private final RtcChatService rtcChatService;

    private Map<String, ChatRoomDto> chatRoomMap;

    @PostConstruct
    private void init() {
        chatRoomMap = new LinkedHashMap<>();
    }

    // 전체 채팅방 조회
    public List<ChatRoomDto> findAllRoom(){
        // 채팅방 생성 순서를 최근순으로 반환
        List<ChatRoomDto> chatRooms = new ArrayList<>(chatRoomMap.values());
        Collections.reverse(chatRooms);

        return chatRooms;
    }

    // roomID 기준으로 채팅방 찾기
    public ChatRoomDto findRoomById(String roomId){
        return chatRoomMap.get(roomId);
    }

    // roomName 로 채팅방 만들기
    public ChatRoomDto createChatRoom(String roomName, String roomPwd, boolean secretChk, int maxUserCnt, String chatType){

        ChatRoomDto room;

        if(chatType.equals("msgChat")){
            room = msgChatService.createChatRoom(chatRoomMap, roomName, roomPwd, secretChk, maxUserCnt);
        }else{
            room = rtcChatService.createChatRoom(chatRoomMap, roomName, roomPwd, secretChk, maxUserCnt);
        }

        return room;
    }

    // 채팅방 비밀번호 조회
    public boolean confirmPwd(String roomId, String roomPwd) {
//        String pwd = chatRoomMap.get(roomId).getRoomPwd();
        return roomPwd.equals(chatRoomMap.get(roomId).getRoomPwd());
    }

    // 채팅방 인원+1
    public void plusUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);
        room.setUserCount(room.getUserCount()+1);
    }

    // 채팅방 인원-1
    public void minusUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);
        room.setUserCount(room.getUserCount()-1);
    }

    // maxUserCnt 에 따른 채팅방 입장 여부
    public boolean chkRoomUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);


        if (room.getUserCount() + 1 > room.getMaxUserCnt()) {
            return false;
        }

        return true;
    }

    public void delChatRoom(String roomId){
        if (chatRoomMap.get(roomId).getChatType().equals(ChatRoomDto.ChatType.MSG)) {
            msgChatService.delChatRoom(chatRoomMap, roomId);
        }else{

        }
    }

}
