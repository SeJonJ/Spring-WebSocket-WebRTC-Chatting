package webChat.batch;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import webChat.Entity.DailyInfo;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.repository.DailyInfoRepository;
import webChat.service.analysis.AnalysisService;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ConcurrentMap;
import java.util.stream.Collectors;

@Component
@Slf4j
@RequiredArgsConstructor
public class RoomBatchJob {

    private final AnalysisService analysisService;
    private final DailyInfoRepository dailyInfoRepository;

    @Scheduled(cron = "0 0,30 * * * *", zone = "Asia/Seoul") // 매 시간 30분에 실행 , 타임존 seoul 기준
    public void checkRoom() {
        // TODO kurento 서버에 대해서 dispose 필요
        ConcurrentMap<String, ChatRoomDto> chatRooms = ChatRoomMap.getInstance().getChatRooms();
        List<String> roomNames = chatRooms.keySet()
                .stream()
                .filter(key -> {
                    return chatRooms.get(key).getUserCount() <= 0; // chatroom 에서 usercount 가 0 이하만 list 로 출력
                })
                .collect(Collectors.toList());

        roomNames.forEach(chatRooms::remove); // map 에서 삭제

        LocalDateTime date = LocalDateTime.now();
        log.info("##########################");
        log.info("Delete room Count : {}", roomNames.size());
        log.info(date.toString());
        log.info("##########################");
    }

//    @Scheduled(cron = "0 0 */3 * * *", zone = "Asia/Seoul") // 3시간 마다 , 타임존 seoul 기준
    @Scheduled(cron = "*/5 * * * * *", zone = "Asia/Seoul")
    public void dailyInfoInsert() {
        LocalDate nowDate = LocalDate.now();
        DailyInfo findDailyInfo = dailyInfoRepository.findByDate(nowDate);
        int dailyVisitor = analysisService.getDailyVisitor();
        int dailyRoomCnt = analysisService.getDailyRoomCnt();

        if (Objects.nonNull(findDailyInfo)) {
            findDailyInfo.setDailyVisitor(dailyVisitor);
            findDailyInfo.setDailyRoomCnt(dailyRoomCnt);
            dailyInfoRepository.save(findDailyInfo);
        } else {
            DailyInfo dailyInfo = DailyInfo.builder()
                    .dailyVisitor(dailyVisitor)
                    .dailyRoomCnt(dailyRoomCnt)
                    .date(nowDate)
                    .build();
            dailyInfoRepository.save(dailyInfo);
        }

        log.info("##########################");
        log.info("dailyVisitor : {}", dailyVisitor);
        log.info("dailyRoomCnt : {}", dailyRoomCnt);
        log.info("##########################");
    }
}
