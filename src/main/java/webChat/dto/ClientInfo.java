package webChat.dto;

import io.micrometer.core.instrument.Tag;
import lombok.Builder;
import lombok.Data;

import java.util.Arrays;
import java.util.List;

@Data
@Builder
public class ClientInfo {
    String ipAddr;
    String subnet;
    String country;
//    String city;
    String countryCode;
    Double latitude;
    Double longitude;
    String timeZone;
    String continentCode;
    boolean isBlack;

    /**
     * clientinfo 의 내용을 prometheus 에서 사용가능한 tag : value 로 변경
     * @param clientInfo
     * @return tag list
     */
    public static List<Tag> toPrometheusMetric(ClientInfo clientInfo){
        List<Tag> tags = Arrays.asList(
                Tag.of("ipAddr", clientInfo.getIpAddr()),
                Tag.of("subnet", clientInfo.getSubnet()),
                Tag.of("country", clientInfo.getCountry()),
                Tag.of("countryCode", clientInfo.getCountryCode()),
                Tag.of("Latitude", clientInfo.getLatitude().toString()),
                Tag.of("Longitude", clientInfo.getLongitude().toString()),
                Tag.of("timeZone", clientInfo.getTimeZone()),
                Tag.of("continentCode", clientInfo.getContinentCode()),
                Tag.of("isBlack", String.valueOf(clientInfo.isBlack()))
        );

        return tags;
    }
}
