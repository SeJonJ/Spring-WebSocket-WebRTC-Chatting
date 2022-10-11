package webChat.service;


import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;
import webChat.Entity.ChatUser;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatUserDto;
import webChat.mapper.ChatUserMapper;


@SpringBootTest
@Transactional
class ChatServiceTest {

    @Autowired
    ChatService repository;

    ChatRoomDto room;

    void createRoom(){
        room = repository.createChatRoom("newTEST", "newPwd", true, 120);
    }

    ChatUser createUser(){
        ChatUser user = ChatUser.builder()
                .id(1L)
                .email("asdf@naver.com")
                .passwd("testPWD")
                .nickName("testNick")
                .provider("naver")
                .build();
        return user;
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

    @Test
    @DisplayName("객체 Mapping")
    void entityToDtoMapping(){
        ChatUserDto dto = ChatUserMapper.INSTANCE.toDto(createUser());

        System.out.println("출력 : "+ dto.getId() + " " + dto.getNickName() + " " + dto.getEmail());
    }
}