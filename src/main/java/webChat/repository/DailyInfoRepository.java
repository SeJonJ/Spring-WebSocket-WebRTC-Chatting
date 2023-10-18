package webChat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import webChat.Entity.DailyInfo;

import java.time.LocalDate;

public interface DailyInfoRepository extends JpaRepository<DailyInfo, Long> {
    DailyInfo findByDate(LocalDate date);
}
