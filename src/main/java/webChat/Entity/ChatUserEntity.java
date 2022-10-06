package webChat.Entity;

import lombok.*;

import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.Id;

@Entity
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatUserEntity {
    @Id
    @GeneratedValue
    private Long id;

    private String nickName;

    private String email;

    private String provider;
}
