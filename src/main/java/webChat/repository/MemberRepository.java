package webChat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import webChat.Entity.ChatUserEntity;

public interface MemberRepository extends JpaRepository<ChatUserEntity, Long> {

}
