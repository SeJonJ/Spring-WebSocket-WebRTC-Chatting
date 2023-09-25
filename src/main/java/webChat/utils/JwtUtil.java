package webChat.utils;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;

public class JwtUtil {

    @Value("${JWT.SECRET_KEY}")
    private String SECRET_KEY = "d2tkNjM5MjU4QA==";

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
                .signWith(SignatureAlgorithm.HS256, SECRET_KEY)
                .compact();
    }

    /**
     * 매개변수로 넘겨받은 token 으로 검증
     * @param token
     * @return 검증 후 true false
     */
    public boolean validateToken(String token) {
        try {
            Jwts.parser().setSigningKey(SECRET_KEY).parseClaimsJws(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
