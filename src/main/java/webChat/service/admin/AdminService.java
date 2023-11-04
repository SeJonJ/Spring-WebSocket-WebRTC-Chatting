package webChat.service.admin;

import java.util.Map;

public interface AdminService {
    Map<String, Object> getAllRooms();

    String delRoom(String roomId);
}
