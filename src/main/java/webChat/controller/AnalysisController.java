package webChat.controller;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import webChat.service.analysis.AnalysisService;

import java.util.Objects;

@RestController
@RequiredArgsConstructor
public class AnalysisController {

    private final AnalysisService analysisService;

    @PostMapping(value = "/visitor", produces="application/json; charset=UTF8")
    public @ResponseBody int getDailyVisitor(
            @RequestParam(defaultValue = "false") Boolean isVisitedToday){
        if(isVisitedToday){
            return analysisService.getDailyVisitor();
        }
        return analysisService.increaseVisitor();
    }
}
