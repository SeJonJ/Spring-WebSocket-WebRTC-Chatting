package webChat.service.monitoring.impl;
import com.maxmind.geoip2.DatabaseReader;
import com.maxmind.geoip2.model.CityResponse;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.HandlerInterceptor;
import webChat.controller.ExceptionController;
import webChat.dto.ClientInfo;
import webChat.service.monitoring.ClientCheckService;
import webChat.service.monitoring.MonitoringService;
import webChat.service.monitoring.PrometheusService;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.InputStream;
import java.net.InetAddress;
import java.util.Objects;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class MonitoringServiceImpl implements MonitoringService,HandlerInterceptor {

    private static final Logger log = LoggerFactory.getLogger(MonitoringServiceImpl.class);

    private final ClientCheckService clientCheckService;
    private final PrometheusService prometheusService;

    // 웹 접속 시 HandlerInterceptor 가 먼저 해당 정보를 인터셉트해와서 정보를 저장
    // prometheus 에 전달한다
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String ipAddress = request.getRemoteAddr();

        log.debug("##########################################");
        log.debug("ipAddrs ::: "+ ipAddress);
        log.debug("ipAddrs ::: "+request.getRemoteHost());
        log.debug("##########################################");

        throw new ExceptionController.InternalServerError("server error");

//        if (Boolean.TRUE.equals(clientCheckService.checkIsAllowedIp(ipAddress))){
//            return true;
//        }
//
//        ClientInfo clientInfo = getClientInfoByAddrs(ipAddress);
//
//        if(Objects.isNull(clientInfo)){
//            throw new ExceptionController.AccessForbiddenException("no clientinfo");
//        }
//
//        Boolean isBlack = clientCheckService.checkBlackList(clientInfo);
//
//        prometheusService.saveCountInfo("access_client_info", clientInfo);
//
//        if(isBlack){
//            // black access 정보만 따로 저장
//            prometheusService.saveCountInfo("black_access_info", clientInfo);
//            throw new ExceptionController.AccessForbiddenException("black ip");
//        }
//        return !isBlack;
    }

    @Override
    public ClientInfo getClientInfoByAddrs(String ipAddress) {
        try {
            InetAddress inetAddress = InetAddress.getByName(ipAddress);
//            ClassPathResource countryResource = new ClassPathResource("geodata/GeoLite2-Country.mmdb");
//            ClassPathResource asnResource = new ClassPathResource("geodata/GeoLite2-ASN.mmdb");
            ClassPathResource cityResource = new ClassPathResource("geodata/GeoLite2-City.mmdb");
//            DatabaseReader cityDataBaseReader = new DatabaseReader.Builder(cityResource.getFile()).build();
            DatabaseReader cityDataBaseReader = null;
            try (InputStream cityResourceInputStream = cityResource.getInputStream()) {
                cityDataBaseReader = new DatabaseReader.Builder(cityResourceInputStream).build();
            }

            Optional<CityResponse> client = cityDataBaseReader.tryCity(inetAddress);
            if(client.isPresent()){
                CityResponse info = client.get();

                return ClientInfo.builder()
                        .ipAddr(info.getTraits().getIpAddress())
                        .subnet(info.getTraits().getNetwork().toString())
                        .country(info.getCountry().getNames().get("en"))
                        .countryCode(info.getCountry().getIsoCode())
                        .latitude(info.getLocation().getLatitude())
                        .longitude(info.getLocation().getLongitude())
                        .timeZone(info.getLocation().getTimeZone())
                        .continentCode(info.getContinent().getCode())
                        .build();
            }

            return null;

        } catch (Exception e) {
//            return ClientInfo.builder().build();
            throw new ExceptionController.AccessForbiddenException("can not find ipAddrs");
        }
    }

//    @Override
//    public Boolean checkBlackList(ClientInfo clientInfo) {
//
//        try {
//            ClassPathResource blackList = new ClassPathResource("geodata/GeoLite2-ASN-Blocks-IPv4.json");
//            InputStream inputStream = blackList.getInputStream();
//            ObjectMapper mapper = new ObjectMapper();
//            JsonNode jsonNode = mapper.readTree(inputStream);
//            return false;
//        } catch (IOException e) {
//            throw new RuntimeException(e);
//        }
//
//    }

}
