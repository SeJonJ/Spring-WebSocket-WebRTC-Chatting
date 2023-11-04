package webChat.batch;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import webChat.Entity.DailyInfo;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.ChatType;
import webChat.dto.KurentoRoomDto;
import webChat.repository.DailyInfoRepository;
import webChat.service.analysis.AnalysisService;
import webChat.service.chat.KurentoManager;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicInteger;

@Component
@Slf4j
@RequiredArgsConstructor
public class RoomBatchJob {
    private final KurentoManager kurentoManager;
    private final AnalysisService analysisService;
    private final DailyInfoRepository dailyInfoRepository;

    @Scheduled(cron = "0 0,30 * * * *", zone = "Asia/Seoul") // 매 시간 30분에 실행 , 타임존 seoul 기준
    public void checkRoom() {
        ConcurrentMap<String, ChatRoomDto> chatRooms = ChatRoomMap.getInstance().getChatRooms();

        AtomicInteger delRoomCnt = new AtomicInteger();
        chatRooms.keySet()
                .forEach(key -> {
                    ChatRoomDto room = chatRooms.get(key);

                    if (room.getUserCount() <= 0) { // chatroom 에서 usercount 가 0 이하만 list 에 저장
                        chatRooms.remove(key);
                        if (room.getChatType().equals(ChatType.RTC)) {
                            kurentoManager.removeRoom((KurentoRoomDto) room);
                        }
                        delRoomCnt.incrementAndGet();
                    }
                });

        LocalDateTime date = LocalDateTime.now();
        log.info("##########################");
        log.info("Delete room Count : {}", delRoomCnt);
        log.info(date.toString());
        log.info("##########################");
    }

    @Scheduled(cron = "0 0 */3 * * *", zone = "Asia/Seoul") // 3시간 마다 , 타임존 seoul 기준
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
