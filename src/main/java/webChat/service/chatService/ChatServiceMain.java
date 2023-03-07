package webChat.service.chatService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.service.fileService.FileService;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ConcurrentMap;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatServiceMain {

    private final MsgChatService msgChatService;
    private final RtcChatService rtcChatService;
    private final FileService fileService;
    private final ConcurrentMap<String, ChatRoomDto> chatRoomMap = ChatRoomMap.getInstance().getChatRooms();

    public List<ChatRoomDto> findAllRoom(){
        List<ChatRoomDto> chatRooms = new ArrayList<>(chatRoomMap.values());
        Collections.reverse(chatRooms);
        return chatRooms;
    }

    public ChatRoomDto findRoomById(String roomId){
        return chatRoomMap.get(roomId);
    }

    public ChatRoomDto createChatRoom(String roomName, String roomPwd, boolean secretChk, int maxUserCnt, String chatType) {
        ChatRoomDto chatRoomDto;
        if (chatType.equals(ChatRoomDto.ChatType.MSG.toString())) {
            chatRoomDto = msgChatService.createChatRoom(roomName, roomPwd, secretChk, maxUserCnt);
        } else {
            chatRoomDto = rtcChatService.createChatRoom(roomName, roomPwd, secretChk, maxUserCnt);
        }
        return chatRoomDto;
    }

    public boolean confirmPwd(String roomId, String roomPwd) {
        return roomPwd.equals(chatRoomMap.get(roomId).getRoomPwd());
    }

    public void plusUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);
        room.setUserCount(room.getUserCount()+1);
    }

    public void minusUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);
        room.setUserCount(room.getUserCount()-1);
    }

    public boolean chkRoomUserCnt(String roomId){
        ChatRoomDto room = chatRoomMap.get(roomId);
        return room.getUserCount() + 1 <= room.getMaxUserCnt();
    }

    public void delChatRoom(String roomId){
        try {
            ChatRoomDto chatRoomDto = chatRoomMap.remove(roomId);
            if (chatRoomDto.getChatType() == ChatRoomDto.ChatType.MSG) {
                fileService.deleteFileDir(roomId);
            }
            log.info("Chat room deleted: roomId={}", roomId);
        } catch (Exception e) {
            log.error("Failed to delete chat room: roomId={}", roomId, e);
        }
    }
}
