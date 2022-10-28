package webChat.rtc;

import com.fasterxml.jackson.databind.ObjectMapper;;
import lombok.RequiredArgsConstructor;
import org.apache.commons.codec.binary.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.WebSocketMessage;
import webChat.service.ChatService.RtcChatService;

import java.io.IOException;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

@Component
@RequiredArgsConstructor
public class SignalHandler extends TextWebSocketHandler {

    private final RtcChatService rtcChatService;

    private final Logger logger = LoggerFactory.getLogger(this.getClass());
    private final ObjectMapper objectMapper = new ObjectMapper();

    // session id to room mapping
    private Map<String, ChatRoomDto> rooms = ChatRoomMap.getInstance().getChatRooms();

    // message types, used in signalling:
    // SDP Offer message
    private static final String MSG_TYPE_OFFER = "offer";
    // SDP Answer message
    private static final String MSG_TYPE_ANSWER = "answer";
    // New ICE Candidate message
    private static final String MSG_TYPE_ICE = "ice";
    // join room data message
    private static final String MSG_TYPE_JOIN = "join";
    // leave room data message
    private static final String MSG_TYPE_LEAVE = "leave";

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        logger.info("[ws] Session has been closed with status [{} {}]", status, session);

    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        // webSocket has been opened, send a message to the client
        // when data field contains 'true' value, the client starts negotiating
        // to establish peer-to-peer connection, otherwise they wait for a counterpart

        // 해결완료!!
        // js 쪽에서 ajax 요청을 통해 rooms 가 아닌 userList 에 몇명이 있는지 확인하고
        // 2명 이상인 경우에만 true 가 되도록 변경
        // 즉 여기서는 true 를 반환하던 false 를 반환하던 무방하고, 결국 ajax 를 통해서 결정됨
        sendMessage(session, new WebSocketMessage("Server", MSG_TYPE_JOIN, Boolean.toString(!rooms.isEmpty()), null, null));
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage textMessage) {
        // a message has been received
        try {
            WebSocketMessage message = objectMapper.readValue(textMessage.getPayload(), WebSocketMessage.class);
            logger.debug("[ws] Message of {} type from {} received", message.getType(), message.getFrom());
            String userUUID = message.getFrom(); // 유저 uuid
            String roomId = message.getData(); // roomId

//            logger.info("Message {}", message.toString());

            ChatRoomDto room;
            switch (message.getType()) {

                // process signal received from client
                case MSG_TYPE_OFFER:
                case MSG_TYPE_ANSWER:
                case MSG_TYPE_ICE:
                    Object candidate = message.getCandidate();
                    Object sdp = message.getSdp();

                    logger.debug("[ws] Signal: {}",
                            candidate != null
                                    ? candidate.toString().substring(0, 64)
                                    : sdp.toString().substring(0, 64));

                    /* 여기도 마찬가지 */
                    ChatRoomDto roomDto = rooms.get(roomId);

                    if (roomDto != null) {
                        Map<String, WebSocketSession> clients = rtcChatService.getClients(roomDto);

                        /*
                         * Map.Entry 는 Map 인터페이스 내부에서 Key, Value 를 쌍으로 다루기 위해 정의된 내부 인터페이스
                         * 보통 key 값들을 가져오는 entrySet() 과 함께 사용한다.
                         * entrySet 을 통해서 key 값들을 불러온 후 Map.Entry 를 사용하면서 Key 에 해당하는 Value 를 쌍으로 가져온다
                         * */
                        for(Map.Entry<String, WebSocketSession> client : clients.entrySet())  {

                            // send messages to all clients except current user
                            if (!client.getKey().equals(userUUID)) {
                                // select the same type to resend signal
                                sendMessage(client.getValue(),
                                        new WebSocketMessage(
                                                userUUID,
                                                message.getType(),
                                                roomId,
                                                candidate,
                                                sdp));
                            }
                        }
                    }
                    break;

                // identify user and their opponent
                case MSG_TYPE_JOIN:
                    // message.data contains connected room id
                    logger.debug("[ws] {} has joined Room: #{}", userUUID, message.getData());

//                    room = rtcChatService.findRoomByRoomId(roomId)
//                            .orElseThrow(() -> new IOException("Invalid room number received!"));
                    room = ChatRoomMap.getInstance().getChatRooms().get(roomId);

                    // add client to the Room clients list
                    rtcChatService.addClient(room, userUUID, session);

                    /* 이 부분에서 session.getID 대신 roomID 를 사용하면 문제 생김*/
                    rooms.put(roomId, room);
                    break;

                case MSG_TYPE_LEAVE:
                    // message data contains connected room id
                    logger.info("[ws] {} is going to leave Room: #{}", userUUID, message.getData());

                    // roomID 기준 채팅방 찾아오기
                    room = rooms.get(message.getData());

                    // room clients list 에서 해당 유저 삭제
                    // 1. room 에서 client List 를 받아와서 keySet 을 이용해서 key 값만 가져온 후 stream 을 사용해서 반복문 실행
                    Optional<String> client = rtcChatService.getClients(room).keySet().stream()
                            // 2. 이때 filter - 일종의 if문 -을 사용하는데 entry 에서 key 값만 가져와서 userUUID 와 비교한다
                            .filter(clientListKeys -> StringUtils.equals(clientListKeys, userUUID))
                            // 3. 하여튼 동일한 것만 가져온다
                            .findAny();

                    // 만약 client 의 값이 존재한다면 - Optional 임으로 isPersent 사용 , null  아니라면 - removeClientByName 을 실행
                    client.ifPresent(userID -> rtcChatService.removeClientByName(room, userID));
                    logger.debug("삭제 완료 [{}] ",client);
                    break;

                // something should be wrong with the received message, since it's type is unrecognizable
                default:
                    logger.debug("[ws] Type of the received message {} is undefined!", message.getType());
                    // handle this if needed
            }

        } catch (IOException e) {
            logger.debug("An error occured: {}", e.getMessage());
        }
    }

    private void sendMessage(WebSocketSession session, WebSocketMessage message) {
        try {
            String json = objectMapper.writeValueAsString(message);
            session.sendMessage(new TextMessage(json));
        } catch (IOException e) {
            logger.debug("An error occured: {}", e.getMessage());
        }
    }
}
