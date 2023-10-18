package webChat.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;
import webChat.Entity.DailyInfo;
import webChat.dto.DailyInfoDto;

@Mapper(componentModel = "spring")

public interface DailyInfoMapper {
    DailyInfo INSTANCE = Mappers.getMapper(DailyInfo.class);

    DailyInfoDto toDto(DailyInfo e);
    DailyInfo toEntity(DailyInfoDto d);
}
