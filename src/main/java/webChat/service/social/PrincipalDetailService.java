package webChat.service.social;

import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

// 시큐리티 설정에서 loginProcess 에 해당하는 요청이 들어왔을 때 아래의 내용이 실행됨
// 더 자세히는 loginProcess 해당하는 "/login" 요청이 들어오면
// UserDetailsService 의 타입으로 IoC(Bean 으로 등록된 클래스) 되어있는 loadUserByUsername 메서드가 실행됨
@Service
public class PrincipalDetailService implements UserDetailsService {


    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        return null;
    }
}
