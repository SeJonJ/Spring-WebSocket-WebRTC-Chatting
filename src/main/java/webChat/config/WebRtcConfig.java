package webChat.config;

import lombok.RequiredArgsConstructor;
import org.kurento.client.KurentoClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.server.standard.ServletServerContainerFactoryBean;
import webChat.rtc.KurentoHandler;

@Configuration
@EnableWebSocket // 웹 소켓에 대해 자동 설정
@RequiredArgsConstructor
public class WebRtcConfig implements WebSocketConfigurer {
    /* TODO WebRTC 관련 */
    // signalHandler 대신 KurentoHandler 사용
//    private final SignalHandler signalHandler;

    // kurento 를 다루기 위한 핸들러
    @Bean
    public KurentoHandler kurentoHandler(){
        return new KurentoHandler();
    }

    // Kurento Media Server 를 사용하기 위한 Bean 설정
    // Bean 으로 등록 후 반드시!! VM 옵션에서 kurento 관련 설정을 해주어야한다.
    // 아니면 에러남
    @Bean
    public KurentoClient kurentoClient() {
        return KurentoClient.create();
    }

    // signal 로 요청이 왔을 때 아래의 WebSockerHandler 가 동작하도록 registry 에 설정
    // 요청은 클라이언트 접속, close, 메시지 발송 등에 대해 특정 메서드를 호출한다
    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(kurentoHandler(), "/signal")
                .setAllowedOrigins("*");
    }

    // 웹 소켓에서 rtc 통신을 위한 최대 텍스트 버퍼와 바이너리 버퍼 사이즈를 설정한다?
    @Bean
    public ServletServerContainerFactoryBean createWebSocketContainer() {
        ServletServerContainerFactoryBean container = new ServletServerContainerFactoryBean();
        container.setMaxTextMessageBufferSize(32768);
        container.setMaxBinaryMessageBufferSize(32768);
        return container;
    }

}
