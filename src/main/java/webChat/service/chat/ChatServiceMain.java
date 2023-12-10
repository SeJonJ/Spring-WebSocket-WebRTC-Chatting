package webChat.service.chat;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.ChatType;
import webChat.dto.KurentoRoomDto;
import webChat.service.analysis.AnalysisService;
import webChat.service.file.FileService;

import java.util.*;


@Service
@Getter
@Setter
@RequiredArgsConstructor
@Slf4j
public class ChatServiceMain {
    private final KurentoManager kurentoManager;
    private final MsgChatService msgChatService;
    private final RtcChatService rtcChatService;

    // 채팅방 삭제에 따른 채팅방의 사진 삭제를 위한 fileService 선언
    private final FileService fileService;

    // 사이트 통계를 위한 서비스
    private final AnalysisService analysisService;


    // 전체 채팅방 조회
    public List<ChatRoomDto> findAllRoom(){
        // TODO room userCnt 로직 수정 필요
        // 채팅방 생성 순서를 최근순으로 반환
        List<ChatRoomDto> chatRooms = new ArrayList<>(ChatRoomMap.getInstance().getChatRooms().values());
        Collections.reverse(chatRooms);

        return chatRooms;
    }

    // roomID 기준으로 채팅방 찾기
    public ChatRoomDto findRoomById(String roomId){
        return ChatRoomMap.getInstance().getChatRooms().get(roomId);
    }

    // roomName 로 채팅방 만들기
    public ChatRoomDto createChatRoom(String roomName, String roomPwd, boolean secretChk, int maxUserCnt, String chatType){

        ChatRoomDto room;

        // 채팅방 타입에 따라서 사용되는 Service 구분
        if(chatType.equals("msgChat")){
            room = msgChatService.createChatRoom(roomName, roomPwd, secretChk, maxUserCnt);
        }else{
            room = rtcChatService.createChatRoom(roomName, roomPwd, secretChk, maxUserCnt);
        }

        analysisService.increaseDailyRoomCnt();

        return room;
    }

    // 채팅방 비밀번호 조회
    public boolean confirmPwd(String roomId, String roomPwd) {
//        String pwd = chatRoomMap.get(roomId).getRoomPwd();

        return roomPwd.equals(ChatRoomMap.getInstance().getChatRooms().get(roomId).getRoomPwd());

    }

    // 채팅방 인원+1
    public void plusUserCnt(String roomId){
        log.info("cnt {}",ChatRoomMap.getInstance().getChatRooms().get(roomId).getUserCount());
        ChatRoomDto room = ChatRoomMap.getInstance().getChatRooms().get(roomId);
        room.setUserCount(room.getUserCount()+1);
    }

    // 채팅방 인원-1
    public void minusUserCnt(String roomId){
        ChatRoomDto room = ChatRoomMap.getInstance().getChatRooms().get(roomId);
        int roomCnt = room.getUserCount()-1;
        if (roomCnt < 0) {
            roomCnt = 0;
        }
        room.setUserCount(roomCnt);
    }

    // maxUserCnt 에 따른 채팅방 입장 여부
    public boolean chkRoomUserCnt(String roomId){
        ChatRoomDto room = ChatRoomMap.getInstance().getChatRooms().get(roomId);

        if (room.getUserCount() + 1 > room.getMaxUserCnt()) {
            return false;
        }

        return true;
    }

    // 채팅방 삭제
    public void delChatRoom(String roomId){

        try {
            ChatRoomDto room = ChatRoomMap.getInstance().getChatRooms().remove(roomId);

            if (room.getChatType().equals(ChatType.RTC)) {
                KurentoRoomDto kurentoRoom = (KurentoRoomDto) room;
                kurentoManager.removeRoom(kurentoRoom);
            }

            // 채팅방 안에 있는 파일 삭제
            fileService.deleteFileDir(roomId);

            log.info("삭제 완료 roomId : {}", roomId);

        } catch (Exception e) { // 만약에 예외 발생시 확인하기 위해서 try catch
            System.out.println(e.getMessage());
        }

    }

}
