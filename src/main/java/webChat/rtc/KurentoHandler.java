package webChat.rtc;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import lombok.RequiredArgsConstructor;
import org.kurento.client.IceCandidate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import webChat.dto.KurentoRoomDto;
import webChat.service.chatService.KurentoManager;
import webChat.service.chatService.KurentoUserRegistry;

import java.io.IOException;

@RequiredArgsConstructor
public class KurentoHandler extends TextWebSocketHandler {

    // 로깅을 위한 객체 생성
    private static final Logger log = LoggerFactory.getLogger(KurentoHandler.class);

    // 데이터를 json 으로 넘겨 받고, 넘기기 때문에 관련 라이브러리로 GSON 을 사용함
    // gson은 json구조를 띄는 직렬화된 데이터를 JAVA의 객체로 역직렬화, 직렬화 해주는 자바 라이브러리 입니다.
    // 즉, JSON Object -> JAVA Object 또는 그 반대의 행위를 돕는 라이브러리 입니다.
    private static final Gson gson = new GsonBuilder().create();

    // 유저 등록? 을 위한 객체 생성
    @Autowired
   private KurentoUserRegistry registry;

   // room 매니저
    @Autowired
    private KurentoManager roomManager;

    // 이전에 사용하던 그 메서드
    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        final JsonObject jsonMessage = gson.fromJson(message.getPayload(), JsonObject.class);

        final KurentoUserSession user = registry.getBySession(session);

        if (user != null) {
            log.debug("Incoming message from user '{}': {}", user.getName(), jsonMessage);
        } else {
            log.debug("Incoming message from new user: {}", jsonMessage);
        }

        // 일전에 내가 만들었던 시그널링 서버와 동일하게 handleTextMessage 파라미터 message 로 값이 들어오면
        // swtich 문으로 해당 message 를 잘라서 사용한다.
        // 이때 message 는 json 형태로 들어온다
        // key : id 에 대하여
        switch (jsonMessage.get("id").getAsString()) {
            case "joinRoom": // value : joinRoom 인 경우
                joinRoom(jsonMessage, session); // joinRoom 메서드를 실행
                break;

            case "receiveVideoFrom": // receiveVideoFrom 인 경우
                // sender 명 - 사용자명 - 과
                final String senderName = jsonMessage.get("sender").getAsString();
                // 유저명을 통해 session 값을 가져온다
                final KurentoUserSession sender = registry.getByName(senderName);
                // jsonMessage 에서 sdpOffer 값을 가져온다
                final String sdpOffer = jsonMessage.get("sdpOffer").getAsString();
                // 이후 receiveVideoFrom 실행 => 아마도 특정 유저로부터 받은 비디오를 다른 유저에게 넘겨주는게 아닌가...?
                user.receiveVideoFrom(sender, sdpOffer);
                break;

            case "leaveRoom": // 유저가 나간 경우
                leaveRoom(user);
                break;

            case "onIceCandidate": // 유저에 대해 IceCandidate 프로토콜을 실행할 때
                JsonObject candidate = jsonMessage.get("candidate").getAsJsonObject();

                if (user != null) {
                    IceCandidate cand = new IceCandidate(candidate.get("candidate").getAsString(),
                            candidate.get("sdpMid").getAsString(), candidate.get("sdpMLineIndex").getAsInt());
                    user.addCandidate(cand, jsonMessage.get("name").getAsString());
                }
                break;

            default:
                break;
        }
    }

    // 유저의 연결이 끊어진 경우
    // 참여자 목록에서 유저 제거
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        KurentoUserSession user = registry.removeBySession(session);
//        roomManager.getRoom(user.getRoomName()).leave(user);
    }

    // 유저가 Room 에 입장했을 때
    private void joinRoom(JsonObject params, WebSocketSession session) throws IOException {
        // json 형태의 params 에서 room 과 name 을 분리해온다
        final String roomName = params.get("room").getAsString();
        final String name = params.get("name").getAsString();
        log.info("PARTICIPANT {}: trying to join room {}", name, roomName);

        // roomName 를 기준으로 room 으 ㄹ가져온다
        KurentoRoomDto room = roomManager.getRoom(roomName);

        // 유저명과 session 을 room 에 넘겨서 room 에 유저 저장
        final KurentoUserSession user = room.join(name, session);

        // 단순히 room 에 저장하는 것 외에도 user 를 저장하기 위한 메서드?
        registry.register(user);
    }

    // 유저가 room 에서 떠났을 때
    private void leaveRoom(KurentoUserSession user) throws IOException {
        // 유저명을 기준으로 room 을 가져온다
        final KurentoRoomDto room = roomManager.getRoom(user.getRoomName());
        // room 에서 유저를 제거하고
        room.leave(user);

        // room 에서 userCount -1
        room.setUserCount(room.getUserCount()-1);

    }

}
