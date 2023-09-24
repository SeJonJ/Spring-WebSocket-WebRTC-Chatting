package webChat.service.adminService;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.springframework.stereotype.Service;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentMap;

@Service
public class AdminServiceImpl implements AdminService{
    @Override
    public Map<String, Object> getAllRooms() {
        Map<String, Object> result = new HashMap<>();

        ConcurrentMap<String, ChatRoomDto> chatRooms = ChatRoomMap.getInstance().getChatRooms();

        JsonArray joRooms = new JsonArray();
        chatRooms.values()
                .forEach(room -> {
                    JsonObject joRoom = new JsonObject();
                    joRoom.addProperty("id", room.getRoomId());
                    joRoom.addProperty("name", room.getRoomName());
                    joRoom.addProperty("pwd", room.getRoomPwd());
                    joRoom.addProperty("isSecret", room.isSecretChk());
                    joRoom.addProperty("type", room.getChatType().toString());
                    joRoom.addProperty("count", room.getUserCount());

                    joRooms.add(joRoom);
                });

        result.put("roomList", joRooms);
        return result;
    }

    @Override
    public String delRoom(String roomId) {
        Optional<ChatRoomDto> chatRoomDto = Optional.ofNullable(ChatRoomMap.getInstance().getChatRooms().get(roomId));

        if (chatRoomDto.isPresent()) {
            ChatRoomMap.getInstance().getChatRooms().remove(roomId);

            return "success del chatroom";
        }

        return "no such room exist";
    }
}