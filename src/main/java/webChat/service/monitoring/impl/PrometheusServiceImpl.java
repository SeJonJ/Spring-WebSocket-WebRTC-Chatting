package webChat.service.monitoring.impl;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import webChat.dto.ClientInfo;
import webChat.service.monitoring.PrometheusService;

@Service
@RequiredArgsConstructor
public class PrometheusServiceImpl implements PrometheusService {

    // prometheus 연결을 위한 registry
    private final MeterRegistry meterRegistry;

    @Override
    public void saveCountInfo(String metric, ClientInfo info) {

        Counter.builder(metric)
                .tags(ClientInfo.toPrometheusMetric(info))
                .register(meterRegistry)
                .increment();

    }

    @Override
    public void saveGaugeInfo(String metric, ClientInfo info) {}
}
