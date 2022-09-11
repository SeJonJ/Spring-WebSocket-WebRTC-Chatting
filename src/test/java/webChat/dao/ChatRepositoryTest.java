package webChat.dao;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import webChat.dto.ChatRoom;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class ChatRepositoryTest {

    @Autowired
    ChatRepository repository;

    ChatRoom room;

    void createRoom(){
        room = repository.createChatRoom("newTEST", "newPwd", true);
    }

    @Test
    void addUser() {
        createRoom();
        String uuid = repository.addUser(room.getRoomId(), "test");
        System.out.println("uuid : " + uuid);
    }

    @Test
    void delUser() {
    }

    @Test
    void getUserName() {
    }

    @Test
    void getUserList() {
    }

    @Test
    void isDuplicateName() {
        addUser();
        String user = repository.isDuplicateName(room.getRoomId(), "test");
        System.out.println("user : " + user);
    }
}