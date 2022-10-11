package webChat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import webChat.Entity.ChatUser;

public interface MemberRepository extends JpaRepository<ChatUser, Long> {

}
