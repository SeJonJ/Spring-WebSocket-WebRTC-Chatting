package webChat.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class MotionController {
    @GetMapping("/motion")
    public String motion(){
        return "motion";
    }
}
