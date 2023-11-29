package webChat.service.monitoring;

import webChat.dto.ClientInfo;

public interface PrometheusService {

    /**
     * prometheus 에 count 타입? 으로 매개변수로 받은 metric 에 info 를 넣는
     * @param metric
     * @param info
     * @return
     */
    void saveCountInfo(String metric, ClientInfo info);

    void saveGaugeInfo(String metric, ClientInfo info);
}
