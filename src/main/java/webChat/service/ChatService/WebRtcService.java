package webChat.service.ChatService;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.WebSocketSession;
import sun.reflect.generics.tree.Tree;
import webChat.dto.ChatRoomDto;
import webChat.util.Parser;

import java.util.*;

@Service
@RequiredArgsConstructor
public class WebRtcService {
    private final Parser parser;

    private final Set<ChatRoomDto> rooms = new TreeSet<>(Comparator.comparing(ChatRoomDto::getRoomId));

    public Set<ChatRoomDto> getRtcChatRooms(){
        final TreeSet<ChatRoomDto> defensiveCopy = new TreeSet<>(Comparator.comparing(ChatRoomDto::getRoomId));
        defensiveCopy.addAll(rooms);

        return defensiveCopy;
    }

    public Boolean addRoom(final ChatRoomDto room) {
        return rooms.add(room);
    }

    public Optional<ChatRoomDto> findRoomByStringId(String sid) {
        return rooms.stream().filter(room ->
                room.getRoomId().equals(parser.parseId(sid).get())).findAny();
    }

    public Map<String, WebSocketSession> getClients(ChatRoomDto chatRoomDto) {
        return Optional.ofNullable(chatRoomDto)
                .map(r -> Collections.unmodifiableMap(r.getClients()))
                .orElse(Collections.emptyMap());
    }

    public WebSocketSession addClient(ChatRoomDto chatRoomDto, String name, WebSocketSession session) {
        return chatRoomDto.getClients().put(name, session);
    }

    public WebSocketSession removeClientByName(ChatRoomDto chatRoomDto, String name) {
        return chatRoomDto.getClients().remove(name);
    }

}
