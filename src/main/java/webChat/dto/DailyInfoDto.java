package webChat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DailyInfoDto {

    private Long id;

    private int visitorCount; // 일일 방문자 수

    private int dailyRoomCreate; // 일일 방 생성 횟수

    private ChatType mostFavoriteType; // 가장 인기있는 타입

    private LocalDate date; // 년월일만 포함하는 날짜
}
