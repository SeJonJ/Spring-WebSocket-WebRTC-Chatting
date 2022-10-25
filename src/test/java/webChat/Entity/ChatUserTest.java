package webChat.Entity;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;
import webChat.repository.ChatUserRepository;
import webChat.service.ChatService.MsgChatService;

@SpringBootTest
@Transactional
@Slf4j
class ChatUserTest {
    @Autowired
    ChatUserRepository chatUserRepository;

    @Autowired
    MsgChatService msgChatService;


    public ChatUser createUser(){
        ChatUser user = ChatUser.builder()
                .nickName("testtest1")
                .passwd("test1")
                .email("test@test.com")
                .provider("naver")
                .build();

        return user;
    }

    @Test
    @DisplayName("유저 테스트")
    public void userTest(){
        chatUserRepository.saveAndFlush(createUser());

        ChatUser user = chatUserRepository.findByEmail("test@test.com");
        log.info("user : [{} {} {}] ", user.getId(), user.getNickName(), user.getProvider());

    }
}