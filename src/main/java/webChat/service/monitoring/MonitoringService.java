package webChat.service.monitoring;
import webChat.dto.ClientInfo;


public interface MonitoringService {
    /**
     * ipAddrs 로 클라이언트 정보 파싱 => country 기준
     * @param ipAddr
     * @return
     */
    ClientInfo getClientInfoByAddrs(String ipAddr);
}
