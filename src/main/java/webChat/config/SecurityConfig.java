package webChat.config;

import org.apache.catalina.Context;
import org.apache.catalina.connector.Connector;
import org.apache.tomcat.util.descriptor.web.SecurityCollection;
import org.apache.tomcat.util.descriptor.web.SecurityConstraint;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.servlet.server.ServletWebServerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.web.SecurityFilterChain;
import webChat.service.social.PrincipalOauth2UserService;

// springSecurity Config
@Configuration
@EnableWebSecurity
public class SecurityConfig  extends WebSecurityConfigurerAdapter {

    @Autowired
    private PrincipalOauth2UserService principalOauth2UserService;

    // Security 를 이용한 각종 권한 접근 경로 등 설정
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.csrf().disable()
                    .authorizeHttpRequests()
                    // "/" 아래로 접근하는 모든 유저에 대해서 허용 => 즉 모든 경로에 대해서 허용
                    // 로그인 안해도 채팅은 가능하기 때문에 로그인 없이도 모든 경로에 접근할 수 있도록 설정
                    .antMatchers("/**").permitAll()
                .and()
                    // Security 의 기본 login 페이지가 아닌 커스텀 페이지를 사용하기 위한 설정
                    // 로그인 페이지 url
                    .formLogin().loginPage("/chatlogin").permitAll()
                    .loginProcessingUrl("/login") // 로그인 요청 url
                    .defaultSuccessUrl("/") // 로그인 완료 시 요청 url
                .and()
                    .logout().logoutUrl("/logout").permitAll() // 로그인 아웃 시 url
                    .logoutSuccessUrl("/") // 성공적으로 로그아웃 햇을 때 url
                .and()
                    .oauth2Login() // 소셜 로그인 사용 여부
                    .loginPage("/chatlogin") // 소셜 로그인 진행 시 사용할 url
                    .userInfoEndpoint()
                    // SNS 로그인이 완료된 뒤 후처리가 필요함. 엑세스토큰+사용자프로필 정보
                    .userService(principalOauth2UserService);
//        http.requiresChannel(channel ->
//                channel.anyRequest().requiresSecure());
    }

}
