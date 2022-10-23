package webChat.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class RtcController {
    @GetMapping("/rtc")
    public String webRTC() {
        return "rtc";
    }
}
