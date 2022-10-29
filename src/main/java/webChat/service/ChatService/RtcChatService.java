package webChat.service.ChatService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.WebSocketMessage;

import java.util.*;
import java.util.function.BiConsumer;

@Slf4j
@RequiredArgsConstructor
@Service
public class RtcChatService {

    // repository substitution since this is a very simple realization

    public ChatRoomDto createChatRoom(String roomName, String roomPwd, boolean secretChk, int maxUserCnt) {
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
        ChatRoomMap.getInstance().getChatRooms().put(room.getRoomId(), room);

        return room;
    }

//    public Set<ChatRoomDto> getRooms() {
//        TreeSet<ChatRoomDto> defensiveCopy = new TreeSet<>(Comparator.comparing(ChatRoomDto::getRoomId));
//        defensiveCopy.addAll(rooms);
//
//        return defensiveCopy;
//    }

    public Optional<ChatRoomDto> findRoomByRoomId(String roomId) {
        // simple get() because of parser errors handling
        return Optional.ofNullable(ChatRoomMap.getInstance().getChatRooms().get(roomId));
    }

    public Map<String, WebSocketSession> getClients(ChatRoomDto room) {
        // unmodifiableMap : read-only 객체를 만들고 싶을 때 사용
        // Collections emptyMap() : 결과를 반환할 시 반환할 데이터가 없거나 내부조직에 의해 빈 데이터가 반환되어야 하는 경우
        // NullPointException 을 방지하기 위하여 반환 형태에 따라 List 나 Map 의 인스턴스를 생성하여 반환하여 처리해야하는 경우
        // size 메서드 등을 체크하고 추가적인 값을 변경하지 않는 경우 Collections.emptyMap() 를 사용하면 매번 동일한 정적 인스턴스가
        // 변환되므라 각 호출에 대한 불필요한 인스턴스 생성하지 않게 되어 메모리 사용량을 줄일 수 있다

        Optional<ChatRoomDto> roomDto = Optional.ofNullable(room);

//        return (Map<String, WebSocketSession>) Optional.ofNullable(room)
//                .map(r -> Collections.unmodifiableMap(r.getUserList()))
//                .orElse(Collections.emptyMap());

        return (Map<String, WebSocketSession>) roomDto.get().getUserList();
    }

    public Map<String, WebSocketSession> addClient(ChatRoomDto room, String name, WebSocketSession session) {
        Map<String, WebSocketSession> userList = (Map<String, WebSocketSession>) room.getUserList();
        userList.put(name, session);
        return userList;
    }

    // userList 에서 클라이언트 삭제
    public void removeClientByName(ChatRoomDto room, String userUUID) {
        room.getUserList().remove(userUUID);
    }

    // 유저 카운터 return
    public boolean findUserCount(WebSocketMessage webSocketMessage){
        ChatRoomDto room = ChatRoomMap.getInstance().getChatRooms().get(webSocketMessage.getData());
//        log.info("ROOM COUNT : [{} ::: {}]",room.toString(),room.getUserList().size());
        return room.getUserList().size() > 1;
    }

    // 이상하게 웹 소켓 연결이 끊어졌을 때 이벤트 처리
    public void forceDisConn(WebSocketSession session){
//        for (Map.Entry<String, ChatRoomDto> rooms : ChatRoomMap.getInstance().getChatRooms().entrySet()) {
//            rooms.getValue().getUserList().remove(session.getId());
//        }

        // ChatRooms 전체를 돌면서 각 방마다 userList 를 가져온 후 session 을 삭제함
        ChatRoomMap.getInstance().getChatRooms().values()
                        .forEach(room ->{
                            room.getUserList().remove(session.getId());
                        });

        log.debug("강제 퇴장 삭제 완료 [{}]", session.getId());
    }
}
