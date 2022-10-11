package webChat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import webChat.Entity.ChatUser;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ChatUserDto {
    // TODO CHATUSERENTITY 에 따라서 전체 뜯어 고치기
    private Long id; // DB 저장되는 id : PK
    private String nickName; // 소셜에서 제공받은 유저명 => 유저 닉네임
    private String email; // 소셜에서 제공받은 이메일
    private String provider; // 소셜 제공자 -> ex) 네이버, 카카오 ----

    // Member 엔티티를
    public static ChatUserDto of(ChatUser chatUserEntity) {
        ChatUserDto chatUserDto = ChatUserDto.builder()
                .id(chatUserEntity.getId())
                .nickName(chatUserEntity.getNickName())
                .email(chatUserEntity.getEmail())
                .provider(chatUserEntity.getProvider())
                .build();

        return chatUserDto;
    }
}
