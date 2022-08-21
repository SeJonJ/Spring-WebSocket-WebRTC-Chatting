package webChat.service;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import webChat.dto.ChatRoom;

@SpringBootTest
class ChatServiceTest {

    @Autowired
    private ChatService service;


    @Test
    void createRoom() {
        ChatRoom room = service.createRoom("TEST");
        System.out.println(room.toString());
    }
}