package webChat.rtc;

import com.fasterxml.jackson.databind.ObjectMapper;;
import lombok.RequiredArgsConstructor;
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
    // text message
    private static final String MSG_TYPE_TEXT = "text";
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
        logger.debug("[ws] Session has been closed with status {}", status);
        rooms.remove(session.getId());
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        // webSocket has been opened, send a message to the client
        // when data field contains 'true' value, the client starts negotiating
        // to establish peer-to-peer connection, otherwise they wait for a counterpart

        // 여기를 고쳐야한다!!!!!
        // 결국 여기서 맨 처음에는 false 가 나와야 한번만 앞쪽 script 에서 peer 연결을 멈추는데
        // 여기가 true 이기 때문에 계속 자기자신한데 peer 요청을 하게되고...
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

            logger.info("Message {}", message.toString());

            ChatRoomDto room;
            switch (message.getType()) {
                // text message from client has been received
                case MSG_TYPE_TEXT:
                    logger.debug("[ws] Text message: {}", message.getData());
                    // message.data is the text sent by client
                    // process text message if needed
                    break;

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
                        *
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
                    logger.debug("[ws] {} is going to leave Room: #{}", userUUID, message.getData());

                    // room id taken by session id
                    room = rooms.get(session.getId());

                    // remove the client which leaves from the Room clients list
                    Optional<String> client = rtcChatService.getClients(room).entrySet().stream()
                            .filter(entry -> Objects.equals(entry.getValue().getId(), session.getId()))
                            .map(Map.Entry::getKey)
                            .findAny();
                    client.ifPresent(c -> rtcChatService.removeClientByName(room, c));
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
