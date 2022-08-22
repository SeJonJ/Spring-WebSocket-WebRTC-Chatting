package webChat.Handler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.handler.TextWebSocketHandler;

@Slf4j
@Component
@RequiredArgsConstructor
public class WebSocketChatHandler_미사용 extends TextWebSocketHandler {
    // 여기의 내용은 ChatController 로 대체!
//    private final ObjectMapper mapper;
//
//    private final ChatService service;
//
//    @Override
//    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
//
//        String payload = message.getPayload();
//        log.info("payload {}", payload);
//
////        TextMessage textMessage = new TextMessage("Welcome Chatting Server");
////        session.sendMessage(textMessage);
//
//        // 웹 소켓 클라이언트로부터 채팅 메시지를 전달받아 채팅 메시지 객체로 변환
//        ChatDTO chatMessage = mapper.readValue(payload, ChatDTO.class);
//        log.info("session {}", chatMessage.toString());
//
//        // 전달받은 메시지에 담긴 채팅방 Id 로 발송 대상 채팅방 정보를 조회
//        ChatRoom room = service.findRoomById(chatMessage.getRoomId());
//        log.info("room {}", room.toString());
//
//        // 해당 채팅방의 모든 session 에 chatMessage 발송
//        room.handleAction(session, chatMessage, service);
//    }
}
