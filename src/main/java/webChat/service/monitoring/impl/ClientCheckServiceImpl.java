package webChat.service.monitoring.impl;

import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import webChat.controller.ExceptionController;
import webChat.dto.ClientInfo;
import webChat.service.monitoring.ClientCheckService;

import javax.annotation.PostConstruct;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.nio.charset.StandardCharsets;
import java.util.BitSet;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ClientCheckServiceImpl implements ClientCheckService {

    private static final Logger log = LoggerFactory.getLogger(ClientCheckServiceImpl.class);

    private final String blackListJsonPath = "geodata/firehol_level1.txt";

    @Value("${endpoint.allowed_subnet}")
    private List<String> allowedSubnet;
    @Value("${endpoint.allowed_ip_addresses}")
    private List<String> allowedIpAddresses;

    @PostConstruct
    private void initBlackListJson() {
        this.blackListJson(blackListJsonPath);
    }

    @Override
    public Boolean checkBlackList(ClientInfo clientInfo) {
        List<String> blackList = blackListJson(blackListJsonPath);
        log.debug("##########################################");
        log.debug("clientInfo :::: " + clientInfo.toString());
        log.debug("##########################################");

        log.debug("##########################################");
        log.debug("blackList ::: " + blackList.toString());
        log.debug("##########################################");

        boolean isBlack = blackList.stream().anyMatch(black -> {
            return clientInfo.getSubnet().equals(black);
        });

        if (isBlack) {
            clientInfo.setBlack(true);
        }
        return isBlack;
    }

    // CIDR 서브넷 체크 로직을 별도의 메소드로 분리
    @Override
    public Boolean checkIsAllowedIp(String ip) {
        if (allowedIpAddresses.contains(ip)) {
            return true;
        }

        for (String cidr : allowedSubnet) {
            try {
                if (isInRange(cidr, ip)) {
                    return true; // 일치하는 경우 즉시 반환
                }
            } catch (UnknownHostException e) {
                e.printStackTrace(); // 에러 로깅
                throw new ExceptionController.AccessDeniedException("Unknow Host");
            }
        }
        return false; // 일치하는 CIDR이 없는 경우
    }

    /**
     * cidr 에 ip 가 속해있는지 검사
     * @param ip
     * @param cidr
     * @return
     * @throws UnknownHostException
     */
    private boolean isInRange(String cidr, String ip) throws UnknownHostException {
        String[] parts = cidr.split("/");
        String ipSection = parts[0];
        int prefix = (parts.length < 2) ? 0 : Integer.parseInt(parts[1]);

        InetAddress ipAddr = InetAddress.getByName(ip);
        BitSet ipBits = BitSet.valueOf(ipAddr.getAddress());

        InetAddress networkAddr = InetAddress.getByName(ipSection);
        BitSet networkBits = BitSet.valueOf(networkAddr.getAddress());

        int maxLength = Math.max(ipBits.length(), networkBits.length());
        if (maxLength < prefix) {
            maxLength = prefix; // CIDR 접두사 길이가 더 긴 경우
        }

        ipBits.clear(prefix, maxLength);
        networkBits.clear(prefix, maxLength);

        return ipBits.equals(networkBits);

    }

    @Cacheable("blackList")
    public List<String> blackListJson(String path) {
        try {
            // classpath 로 blackList txt 파일 가져오기
            ClassPathResource blackList = new ClassPathResource(path);

            log.debug("blackList URI :: " + blackList.getURI());

            try (InputStream inputStream = blackList.getInputStream()) {
                return new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))
                        .lines()
                        .collect(Collectors.toList());
            }

        } catch (Exception e) {
            log.error("error path :: " + path);
            throw new ExceptionController.ResourceNotFoundException("there is No BlackList file");
        }
    }
}
