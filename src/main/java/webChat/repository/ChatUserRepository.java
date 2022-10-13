package webChat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import webChat.Entity.ChatUser;

public interface ChatUserRepository extends JpaRepository<ChatUser, Long> {
    ChatUser findByEmail(String email);
}
