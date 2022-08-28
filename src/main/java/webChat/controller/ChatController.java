package webChat.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.json.simple.JSONArray;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessageSendingOperations;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.socket.messaging.SessionDisconnectEvent;
import webChat.dto.ChatDTO;

import java.util.ArrayList;
import java.util.HashMap;


@Slf4j
@RequiredArgsConstructor
@Controller
public class ChatController {

    HashMap<String, ArrayList<String>> users = new HashMap<>();

    private final SimpMessageSendingOperations template;

    // MessageMapping 을 통해 webSocket 로 들어오는 메시지를 발신 처리한다.
    // 이때 클라이언트에서는 /pub/chat/message 로 요청하게 되고 이것을 controller 가 받아서 처리한다.
    // 처리가 완료되면 /sub/chat/room/roomId 로 메시지가 전송된다.
    @MessageMapping("/chat/enterUser")
    public void enterUser(@Payload ChatDTO chat, SimpMessageHeaderAccessor headerAccessor) {
        headerAccessor.getSessionAttributes().put("username", chat.getSender());
        headerAccessor.getSessionAttributes().put("roomId", chat.getRoomId());

        users.put(chat.getRoomId(), new ArrayList<String>());
        users.get(chat.getRoomId()).add(chat.getSender());
        ArrayList<String> arr = users.get(chat.getRoomId());

                chat.setMessage(chat.getSender() + " 님 입장!!");
        template.convertAndSend("/sub/chat/room/" + chat.getRoomId(), chat);

    }

    // 이후 /sub/chat/room/roomId 를 구독하고 있는 구독자(클라이언트)들이 /sub/chat/room/roomId 로 날아온 메시지를
    // 구독(subscribe, 수신)하고 view 에서 볼 수 있게 된다.
    @MessageMapping("/chat/sendMessage")
    public void sendMessage(@Payload ChatDTO chat) {
        log.info("CHAT {}", chat);
        chat.setMessage(chat.getMessage());
        template.convertAndSend("/sub/chat/room/" + chat.getRoomId(), chat);

    }

    @EventListener
    public void handleWebSocketDisconnectListener(SessionDisconnectEvent event) {
        log.info("DisConnEvent {}", event);
        StompHeaderAccessor headerAccessor = StompHeaderAccessor.wrap(event.getMessage());
        String username = (String) headerAccessor.getSessionAttributes().get("username");
        String roomId = (String)headerAccessor.getSessionAttributes().get("roomId");

        log.info("headAccessor {}", headerAccessor);

        if (username != null) {
            log.info("User Disconnected : " + username);

            ChatDTO chatMessage = new ChatDTO();
            chatMessage.setType(ChatDTO.MessageType.LEAVE);
            chatMessage.setSender(username);
            chatMessage.setMessage(username + " 님 퇴장!!");

            template.convertAndSend("/sub/chat/room/" + roomId, chatMessage);
        }
    }


}
