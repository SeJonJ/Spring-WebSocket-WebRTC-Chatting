package webChat.service.social;

public interface SocialLogin {
    String getProvider(); // 소셜 로그인 제공자 정보
    String getEmail(); // 소셜 로그인 이메일 정보
    String getNickName(); // 소셜 로그인 닉네임 정보
}
