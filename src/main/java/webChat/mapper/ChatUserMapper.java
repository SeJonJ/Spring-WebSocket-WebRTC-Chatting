package webChat.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;
import webChat.Entity.ChatUser;
import webChat.dto.ChatUserDto;

@Mapper(componentModel = "spring")
public interface ChatUserMapper {
    ChatUserMapper INSTANCE = Mappers.getMapper(ChatUserMapper.class);

    ChatUserDto toDto(ChatUser e);
    ChatUser toEntity(ChatUserDto d);
}
