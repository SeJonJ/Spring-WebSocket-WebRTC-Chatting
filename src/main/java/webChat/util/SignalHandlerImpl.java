package webChat.util;

import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import webChat.dto.SignalMessageDto;

import java.util.HashMap;
import java.util.Map;

/* TODO WebRTC 관련 */
@Component
@RequiredArgsConstructor
public class SignalHandlerImpl extends TextWebSocketHandler implements SignalMessageTypeInter {

    private static final Logger LOG = LoggerFactory.getLogger(SignalHandlerImpl.class);

    private static final String TYPE_INIT = "init";
    private static final String TYPE_LOGOUT = "logout";

    /**
     * Cache of sessions by users.
     */
    private final Map<String, WebSocketSession> connectedUsers = new HashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        LOG.info("[" + session.getId() + "] Connection established " + session.getId());

        // send the message to all other peers, that new men its being registered
        SignalMessageDto newMenOnBoard = new SignalMessageDto();
        newMenOnBoard.setType(TYPE_INIT);
        newMenOnBoard.setSender(session.getId());

        connectedUsers.values().forEach(webSocketSession -> {
            try {
                webSocketSession.sendMessage(new TextMessage(Utils.getString(newMenOnBoard)));
            } catch (Exception e) {
                LOG.warn("Error while message sending.", e);
            }
        });

        // put the session to the "cache".
        connectedUsers.put(session.getId(), session);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        LOG.info("[" + session.getId() + "] Connection closed " + session.getId() + " with status: " + status.getReason());
        removeUserAndSendLogout(session.getId());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        LOG.info("[" + session.getId() + "] Connection error " + session.getId() + " with status: " + exception.getLocalizedMessage());
        removeUserAndSendLogout(session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        LOG.info("handleTextMessage : {}", message.getPayload());

        SignalMessageDto signalMessage = Utils.getObject(message.getPayload());

        // with the destinationUser find the targeted socket, if any
        String destinationUser = signalMessage.getReceiver();
        WebSocketSession destSocket = connectedUsers.get(destinationUser);
        // if the socket exists and is open, we go on
        if (destSocket != null && destSocket.isOpen()) {
            // set the sender as current sessionId.
            signalMessage.setSender(session.getId());
            final String resendingMessage = Utils.getString(signalMessage);
            LOG.info("send message {} to {}", resendingMessage, destinationUser);
            destSocket.sendMessage(new TextMessage(resendingMessage));
        }
    }

    private void removeUserAndSendLogout(final String sessionId) {

        connectedUsers.remove(sessionId);

        // send the message to all other peers, somebody(sessionId) leave.
        SignalMessageDto menOut = new SignalMessageDto();
        menOut.setType(TYPE_LOGOUT);
        menOut.setSender(sessionId);

        connectedUsers.values().forEach(webSocket -> {
            try {
                webSocket.sendMessage(new TextMessage(Utils.getString(menOut)));
            } catch (Exception e) {
                LOG.warn("Error while message sending.", e);
            }
        });
    }
}
