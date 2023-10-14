package webChat.batch;

import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ConcurrentMap;
import java.util.stream.Collectors;

@Component
@Slf4j
public class RoomBatchJob {

    @Scheduled(cron = "0 0,30 * * * *", zone="Asia/Seoul") // 매 시간 30분에 실행 , 타임존 seoul 기준
    public void checkRoom(){

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
}
