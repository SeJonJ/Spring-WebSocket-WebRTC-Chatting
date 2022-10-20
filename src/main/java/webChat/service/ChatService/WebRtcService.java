package webChat.service.ChatService;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import sun.reflect.generics.tree.Tree;
import webChat.dto.ChatRoomDto;

import java.util.Comparator;
import java.util.Set;
import java.util.TreeSet;

@Service
@RequiredArgsConstructor
public class WebRtcService {
    private final Parser Parser;

    private final Set<ChatRoomDto> rooms = new TreeSet<>(Comparator.comparing(ChatRoomDto::getRoomId));

    public Set<ChatRoomDto> getRtcChatRooms(){
        final TreeSet<ChatRoomDto> defensiveCopy = new TreeSet<>(Comparator.comparing(ChatRoomDto::getRoomId));
        defensiveCopy.addAll(rooms)

        return defensiveCopy;
    }

    public Boolean addRoom(final ChatRoomDto room) {
        return rooms.add(room);
    }
}
