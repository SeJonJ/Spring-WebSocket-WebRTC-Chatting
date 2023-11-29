package webChat.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import webChat.service.monitoring.impl.MonitoringServiceImpl;

// 인터셉터를 위한 config 설정
// HandlerInterceptor 를 사용하기 WebMvcConfigurer 를 구현한 클래스에 registry 에
// intercepter 하려는 클래스를 등록해야한다.
@Configuration
@RequiredArgsConstructor
public class MonitoringConfig implements WebMvcConfigurer {
    private final MonitoringServiceImpl monitoringServiceImpl;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // addInterceptors 의 파라미터에는 HandlerInterceptor 를 구현한 구현체 클래스를 넣는다
        // addPathPatterns 는 특정한 패턴 즉 특정한 요청에 대해서만 인터셉터 가능!
        registry.addInterceptor(monitoringServiceImpl)
                .addPathPatterns("/");
    }
}
