package webChat.controller;

import com.google.gson.Gson;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import webChat.service.admin.AdminService;
import webChat.utils.JwtUtil;

import java.util.Map;

@RestController
@RequiredArgsConstructor
public class AdminController {

    private final AdminService adminService;

    @PostMapping("/gentoken/{key}")
    public String generateToken(@PathVariable String key) throws Exception {
        return JwtUtil.getInstance().generateToken(key);
    }

    /**
     * room list return
     *
     * @param token
     * @return room list
     * @throws Exception 400, 401
     */
    @PostMapping("/allrooms")
    public String allRooms(@RequestHeader("Authorization") String token) throws Exception {

        String jwtToken = token.replace("Bearer ", "");

        if (!token.startsWith("Bearer ")) {
            throw new ExceptionController.UnauthorizedException("Invalid token format");
        }

        if (!JwtUtil.getInstance().validateToken(jwtToken)) {
            throw new ExceptionController.UnauthorizedException("Invalid token format or you have No Auth");
        }

        try {
            Map<String, Object> result = adminService.getAllRooms();
            return new Gson().toJson(result);
        } catch (Exception e) {
            throw new ExceptionController.InternalServerError(e.getMessage());
        }


    }

    /**
     * roomId 를 받아서 해당 room 삭제
     *
     * @param roomId
     * @param token
     * @return del room result
     * @throws Exception 400, 401
     */
    @PostMapping("/delete/{roomId}")
    public String delRoom(@PathVariable String roomId, @RequestHeader("Authorization") String token) throws Exception {
        String jwtToken = token.replace("Bearer ", "");

        if (!token.startsWith("Bearer ")) {
            throw new ExceptionController.UnauthorizedException("Invalid token format");
        }

        if (!JwtUtil.getInstance().validateToken(jwtToken)) {
            throw new ExceptionController.UnauthorizedException("Invalid token format or you have No Auth");
        }

        try {
            return adminService.delRoom(roomId);
        } catch (Exception e) {
            throw new ExceptionController.InternalServerError(e.getMessage());
        }

    }
}
