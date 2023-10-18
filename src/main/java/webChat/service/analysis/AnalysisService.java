package webChat.service.analysis;

public interface AnalysisService {
    int getDailyVisitor();
    int getDailyRoomCnt();
    int increaseVisitor();
    int decreaseVisitor();
    int increaseDailyRoomCnt();
    int decreaseDailyRoomCnt();
    void resetDailyInfo();
}
