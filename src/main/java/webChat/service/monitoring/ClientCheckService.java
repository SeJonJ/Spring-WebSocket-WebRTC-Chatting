package webChat.service.monitoring;

import webChat.dto.ClientInfo;

import java.util.List;

/**
 * clientinfo 객체로 여러 체크 로직 구현하기 위한 서비스
 */
public interface ClientCheckService {

    /**
     * clientInfo 의 ipAddrs 를 기준으로 블랙리스트인지 체크
     * @param clientInfo
     * @return
     */
    Boolean checkBlackList(ClientInfo clientInfo);

    Boolean checkIPsInSubnet(List<String> ipList, String cidr);
}
