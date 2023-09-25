package webChat.utils;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import javax.annotation.PostConstruct;
import java.util.Date;

// TODO secretKey 세팅 로직 수정 필요!!
@Component
public class JwtUtil {

    @Value("${JWT.SECRET_KEY}")
    private String secretKey;

    public static String SECRET_KEY;

    @PostConstruct
    private void setData(){
        JwtUtil.SECRET_KEY = secretKey;
    }

    private static JwtUtil jwtUtil = new JwtUtil();

    public static JwtUtil getInstance() {
        return jwtUtil;
    }

    /**
     * 토큰 생성
     * @param key
     * @return 인코딩한 토큰 return
     */
    public String generateToken(String key) {
        return Jwts.builder()
                .setSubject(key)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 10))  // 10 hours token validity
                .signWith(SignatureAlgorithm.HS256, JwtUtil.SECRET_KEY)
                .compact();
    }

    /**
     * 매개변수로 넘겨받은 token 으로 검증
     * @param token
     * @return 검증 후 true false
     */
    public boolean validateToken(String token) {
        try {
            Jwts.parser().setSigningKey(JwtUtil.SECRET_KEY).parseClaimsJws(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
