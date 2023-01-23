package webChat.mapper;

import javax.annotation.Generated;
import org.springframework.stereotype.Component;
import webChat.Entity.ChatUser;
import webChat.Entity.ChatUser.ChatUserBuilder;
import webChat.dto.ChatUserDto;
import webChat.dto.ChatUserDto.ChatUserDtoBuilder;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2023-01-21T17:39:45+0900",
    comments = "version: 1.4.2.Final, compiler: javac, environment: Java 11.0.11 (AdoptOpenJDK)"
)
@Component
public class ChatUserMapperImpl implements ChatUserMapper {

    @Override
    public ChatUserDto toDto(ChatUser e) {
        if ( e == null ) {
            return null;
        }

        ChatUserDtoBuilder chatUserDto = ChatUserDto.builder();

        chatUserDto.id( e.getId() );
        chatUserDto.nickName( e.getNickName() );
        chatUserDto.passwd( e.getPasswd() );
        chatUserDto.email( e.getEmail() );
        chatUserDto.provider( e.getProvider() );

        return chatUserDto.build();
    }

    @Override
    public ChatUser toEntity(ChatUserDto d) {
        if ( d == null ) {
            return null;
        }

        ChatUserBuilder chatUser = ChatUser.builder();

        chatUser.id( d.getId() );
        chatUser.nickName( d.getNickName() );
        chatUser.email( d.getEmail() );
        chatUser.passwd( d.getPasswd() );
        chatUser.provider( d.getProvider() );

        return chatUser.build();
    }
}
