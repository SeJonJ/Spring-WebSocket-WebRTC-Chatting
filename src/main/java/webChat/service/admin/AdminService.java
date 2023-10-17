package webChat.service.admin;

import java.util.Map;

public interface AdminService {
    public Map<String, Object> getAllRooms();

    public String delRoom(String roomId);
}
