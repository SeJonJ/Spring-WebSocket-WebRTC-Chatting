package webChat.Entity;

import lombok.*;
import webChat.dto.ChatType;

import javax.persistence.*;
import java.time.LocalDate;

@Entity
@Table
@Setter
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DailyInfo {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column
    private int dailyVisitor; // 일일 방문자 수

    @Column
    private int dailyRoomCnt; // 일일 방 생성 횟수

    @Column
    @Enumerated(EnumType.STRING)
    private ChatType mostFavoriteType; // 가장 인기있는 타입

    @Column
    private LocalDate date; // 년월일만 포함하는 날짜
}
