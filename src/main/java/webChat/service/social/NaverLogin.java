package webChat.service.social;

import java.util.Map;

public class NaverLogin implements SocialLogin{
    private Map<String, Object> naverAttributes;


    public NaverLogin(Map<String, Object> naverAttributes) {

        this.naverAttributes = naverAttributes;
    }

    @Override
    public String getProvider() {
        // TODO Auto-generated method stub

        return "naver";
    }

    @Override
    public String getEmail() {
        // TODO Auto-generated method stub
        Map<String, Object> map = (Map<String, Object>) naverAttributes.get("response");

        return (String) map.get("email");
    }

    @Override
    public String getNickName() {
        // TODO Auto-generated method stub
        Map<String, Object> map = (Map<String, Object>) naverAttributes.get("response");
        return (String) map.get("nickname");
    }
}
