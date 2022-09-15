package webChat.service.social;

import java.util.HashMap;
import java.util.Map;

public class KaKaoLogin implements SocialLogin{

    private Map<String, Object> kakaoAttributes;


    public KaKaoLogin(Map<String, Object> kakaoAttributes) {
        this.kakaoAttributes = kakaoAttributes;
    }


    @Override
    public String getProvider() {
        // TODO Auto-generated method stub

        return "kakao";
    }

    @Override
    public String getEmail() {
        // TODO Auto-generated method stub
        HashMap<String, Object> account = (HashMap<String, Object>) kakaoAttributes.get("kakao_account");

        String email = (String) account.get("email"); // 이메일 가져오기
//		System.out.println("memail : "+memail);

        return email;
    }

    @Override
    public String getNickName() {
        // TODO Auto-generated method stub
        HashMap<String, Object> properties = (HashMap<String, Object>) kakaoAttributes.get("properties");
        String nickName = (String) properties.get("nickname"); // 닉네임 가져오기

        return nickName;
    }
}
