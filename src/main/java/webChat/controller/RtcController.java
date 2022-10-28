package webChat.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import webChat.dto.WebSocketMessage;
import webChat.service.ChatService.RtcChatService;

@RestController
@RequiredArgsConstructor
@Slf4j
public class RtcController {

    private final RtcChatService rtcChatService;

    @PostMapping("/webrtc/usercount")
    public boolean webRTC(@ModelAttribute WebSocketMessage webSocketMessage) {
        log.info("MESSAGE : {}",webSocketMessage.toString());
        return rtcChatService.findUserCount(webSocketMessage);
    }
}
