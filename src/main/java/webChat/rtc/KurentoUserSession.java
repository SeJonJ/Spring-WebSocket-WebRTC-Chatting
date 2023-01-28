/*
 * (C) Copyright 2014 Kurento (http://kurento.org/)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

package webChat.rtc;

import com.google.gson.JsonObject;
import lombok.RequiredArgsConstructor;
import org.kurento.client.*;
import org.kurento.jsonrpc.JsonUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.Closeable;
import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 *
 * @modifyBy SeJon Jang (wkdtpwhs@gmail.com)
 * @desc 결국엔 여기서 중요한 것은 현재의 '나' 의 webRtcEndPoint 객체와 다른 사람들의 webRtcEndPoint 객체를 저장한 map 을 확인하고
 * 새로운 유저가 들어왔을 때 이를 나의 map 에 저장하고, 다른 사람들과 이를 동기화 해서 일치 시키는 것?
 */
@RequiredArgsConstructor
public class KurentoUserSession implements Closeable {

  private static final Logger log = LoggerFactory.getLogger(KurentoUserSession.class);

  private final String name;
  private final WebSocketSession session;

  private final MediaPipeline pipeline;

  private final String roomName;

  /**
   * @desc 현재 '나' 의 webRtcEndPoint 객체
   * 나의 것이니까 밖으로 내보낸다는 의미의 outgoingMedia
   * */
  private final WebRtcEndpoint outgoingMedia;

  /**
   * @desc '나'와 연결된 다른 사람의 webRtcEndPoint 객체 => map 형태로 유저명 : webRtcEndPoint 로 저장됨
   * 다른 사람꺼니까 받는다는 의미의 incomingMedia
   * */
  private final ConcurrentMap<String, WebRtcEndpoint> incomingMedia = new ConcurrentHashMap<>();

  /**
   * @Param String 유저명, String 방이름, WebSocketSession 세션객체, MediaPipline (kurento)mediaPipeline 객체
   */
  public KurentoUserSession(String name, String roomName, WebSocketSession session,
                            MediaPipeline pipeline) {

    this.pipeline = pipeline;
    this.name = name;
    this.session = session;
    this.roomName = roomName;

    // 외부로 송신하는 미디어?
    this.outgoingMedia = new WebRtcEndpoint.Builder(pipeline).build();

    // iceCandidateFounder 이벤트 리스너 등록
    // 이벤트가 발생했을 때 다른 유저들에게 새로운 iceCnadidate 후보를 알림
    this.outgoingMedia.addIceCandidateFoundListener(new EventListener<IceCandidateFoundEvent>() {


      @Override
      public void onEvent(IceCandidateFoundEvent event) {
        // JsonObject 생성
        JsonObject response = new JsonObject();
        // id : iceCnadidate, id 는 ice후보자 선정
        response.addProperty("id", "iceCandidate");
        // name : 유저명
        response.addProperty("name", name);

        // add 랑 addProperty 랑 차이점?
        // candidate 를 key 로 하고, IceCandidateFoundEvent 객체를 JsonUtils 를 이용해
        // json 형태로 변환시킨다 => toJsonObject 는 넘겨받은 Object 객체를 JsonObject 로 변환
        response.add("candidate", JsonUtils.toJsonObject(event.getCandidate()));

        try {
          /** synchronized 안에는 동기화 필요한 부분 지정*/
          // 먼저 동기화는 프로세스(스레드)가 수행되는 시점을 조절하여 서로가 알고 있는 정보가 일치하는 것
          // 여기서는 쉽게 말해 onEvent 를 통해서 넘어오는 모든 session 객체에게 앞에서 생성한 response json 을
          // 넘겨주게되고 이를 통해서 iceCandidate 상태를 '일치' 시킨다? ==> 여긴 잘 모르겟어요...
          synchronized (session) {
            session.sendMessage(new TextMessage(response.toString()));
          }
        } catch (IOException e) {
          log.debug(e.getMessage());
        }
      }
    });
  }

  /**
   * @desc 나의 webRtcEndpoint 객체를 return 함
   * @return webRtcEndpoint 객체
   * */
  public WebRtcEndpoint getOutgoingWebRtcPeer() {
    return outgoingMedia;
  }

  /**
   * @desc IncomingMedia return
   * @return ConcurrentMap<String, WebRtcEndpoint>
   */
  public ConcurrentMap<String, WebRtcEndpoint> getIncomingMedia() {
    return incomingMedia;
  }

  /**
   * @desc 이름 return
   * */
  public String getName() {
    return name;
  }

  /**
   * @desc webSocketSession 객체 return
   * */
  public WebSocketSession getSession() {
    return session;
  }

  /**
   * The room to which the user is currently attending.
   *
   * @return The room
   */
  public String getRoomName() {
    return this.roomName;
  }

  /**
   * @desc
   * @Param userSession, String
   * */
  public void receiveVideoFrom(KurentoUserSession sender, String sdpOffer) throws IOException {
    // 유저가 room 에 들어왓음을 알림
    log.info("USER {}: connecting with {} in room {}", this.name, sender.getName(), this.roomName);

    // 들어온 유저가 Sdp 제안
    log.trace("USER {}: SdpOffer for {} is {}", this.name, sender.getName(), sdpOffer);

    /**
     *
     *  @Desc sdpOffer 에 대한 결과 String
     */
    final String ipSdpAnswer = this.getEndpointForUser(sender).processOffer(sdpOffer);

    final JsonObject scParams = new JsonObject();
    scParams.addProperty("id", "receiveVideoAnswer");
    scParams.addProperty("name", sender.getName());
    scParams.addProperty("sdpAnswer", ipSdpAnswer);

    log.trace("USER {}: SdpAnswer for {} is {}", this.name, sender.getName(), ipSdpAnswer);
    this.sendMessage(scParams);
    log.debug("gather candidates");
    this.getEndpointForUser(sender).gatherCandidates();
  }

  /**
   * @Desc userSession 을 통해서 해당 유저의 WebRtcEndPoint 객체를 가져옴
   * @Param UserSession : 보내는 유저의 userSession 객체
   * @return WebRtcEndPoint
   * */
  private WebRtcEndpoint getEndpointForUser(final KurentoUserSession sender) {
    // 만약 sender 명이 현재 user명과 일치한다면, 즉 sdpOffer 제안을 보내는 쪽과 받는 쪽이 동일하다면?
    // loopback 임을 찍고, 그대로 outgoinMedia 를 return
    if (sender.getName().equals(name)) {
      log.debug("PARTICIPANT {}: configuring loopback", this.name);
      return outgoingMedia;
    }

    // 참여자 name 이 sender 로부터 비디오를 받음을 확인
    log.debug("PARTICIPANT {}: receiving video from {}", this.name, sender.getName());

    // sender 의 이름으로 나의 incomingMedia 에서 sender 의 webrtcEndpoint 객체를 가져옴
    WebRtcEndpoint incoming = incomingMedia.get(sender.getName());

    // 만약 가져온 incoming 이 null 이라면
    // 즉 현재 내가 갖고 있는 incomingMedia 에 sender 의 webrtcEndPoint 객체가 없다면
    if (incoming == null) {
      // 새로운 endpoint 가 만들어졌음을 확인
      log.debug("PARTICIPANT {}: creating new endpoint for {}", this.name, sender.getName());

      // 새로 incoming , 즉 webRtcEndpoint 를 만들고
      incoming = new WebRtcEndpoint.Builder(pipeline).build();

      // incoming 객체의 addIceCandidateFoundListener 메서드 실행
      incoming.addIceCandidateFoundListener(new EventListener<IceCandidateFoundEvent>() {

        @Override
        public void onEvent(IceCandidateFoundEvent event) {
          // json 오브젝트 생성
          JsonObject response = new JsonObject();

          // { id : "iceCandidate"}
          response.addProperty("id", "iceCandidate");
          // { name : sender 의 유저명}
          response.addProperty("name", sender.getName());
          // {candidate : { event.getCandidate 를 json 으로 만든 형태 }
          response.add("candidate", JsonUtils.toJsonObject(event.getCandidate()));
          try {
            // 새로 webRtcEndpoint 가 만들어 졌기 때문에 모든 UserSession 이 이것을 동일하게 공유해야 할 필요가 있다.
            // 즉 모든 UserSession 의 정보를 일치시키기 위해 동기화 - synchronized - 실행
            // 이를 통해서 모든 user 의 incomingMedia 가 동일하게 일치 - 동기화 - 됨
            synchronized (session) {
              session.sendMessage(new TextMessage(response.toString()));
            }
          } catch (IOException e) {
            log.debug(e.getMessage());
          }
        }
      });

      // incomingMedia 에 유저명과 새로 생성된 incoming - webrtcEndPoint 객체 - 을 넣어준다
      incomingMedia.put(sender.getName(), incoming);
    }

    log.debug("PARTICIPANT {}: obtained endpoint for {}", this.name, sender.getName());

    /** 여기가 이해가 안갔었음 */
    // sender 기존에 갖고 있던 webRtcEndPoint 와 새로 생성된 incoming 을 연결한다
    sender.getOutgoingWebRtcPeer().connect(incoming);

    return incoming;
  }

  public void cancelVideoFrom(final KurentoUserSession sender) {
    this.cancelVideoFrom(sender.getName());
  }

  public void cancelVideoFrom(final String senderName) {
    log.debug("PARTICIPANT {}: canceling video reception from {}", this.name, senderName);
    final WebRtcEndpoint incoming = incomingMedia.remove(senderName);

    log.debug("PARTICIPANT {}: removing endpoint for {}", this.name, senderName);
    incoming.release(new Continuation<Void>() {
      @Override
      public void onSuccess(Void result) throws Exception {
        log.trace("PARTICIPANT {}: Released successfully incoming EP for {}",
                KurentoUserSession.this.name, senderName);
      }

      @Override
      public void onError(Throwable cause) throws Exception {
        log.warn("PARTICIPANT {}: Could not release incoming EP for {}", KurentoUserSession.this.name,
                senderName);
      }
    });
  }

  @Override
  public void close() throws IOException {
    log.debug("PARTICIPANT {}: Releasing resources", this.name);
    for (final String remoteParticipantName : incomingMedia.keySet()) {

      log.trace("PARTICIPANT {}: Released incoming EP for {}", this.name, remoteParticipantName);

      final WebRtcEndpoint ep = this.incomingMedia.get(remoteParticipantName);

      ep.release(new Continuation<Void>() {

        @Override
        public void onSuccess(Void result) throws Exception {
          log.trace("PARTICIPANT {}: Released successfully incoming EP for {}",
                  KurentoUserSession.this.name, remoteParticipantName);
        }

        @Override
        public void onError(Throwable cause) throws Exception {
          log.warn("PARTICIPANT {}: Could not release incoming EP for {}", KurentoUserSession.this.name,
                  remoteParticipantName);
        }
      });
    }

    outgoingMedia.release(new Continuation<Void>() {

      @Override
      public void onSuccess(Void result) throws Exception {
        log.trace("PARTICIPANT {}: Released outgoing EP", KurentoUserSession.this.name);
      }

      @Override
      public void onError(Throwable cause) throws Exception {
        log.warn("USER {}: Could not release outgoing EP", KurentoUserSession.this.name);
      }
    });
  }

  public void sendMessage(JsonObject message) throws IOException {
    log.debug("USER {}: Sending message {}", name, message);
    synchronized (session) {
      session.sendMessage(new TextMessage(message.toString()));
    }
  }

  public void addCandidate(IceCandidate candidate, String name) {
    if (this.name.compareTo(name) == 0) {
      outgoingMedia.addIceCandidate(candidate);
    } else {
      WebRtcEndpoint webRtc = incomingMedia.get(name);
      if (webRtc != null) {
        webRtc.addIceCandidate(candidate);
      }
    }
  }

  /*
   * (non-Javadoc)
   *
   * @see java.lang.Object#equals(java.lang.Object)
   */
  @Override
  public boolean equals(Object obj) {

    if (this == obj) {
      return true;
    }
    if (obj == null || !(obj instanceof KurentoUserSession)) {
      return false;
    }
    KurentoUserSession other = (KurentoUserSession) obj;
    boolean eq = name.equals(other.name);
    eq &= roomName.equals(other.roomName);
    return eq;
  }

  /*
   * (non-Javadoc)
   *
   * @see java.lang.Object#hashCode()
   */
  @Override
  public int hashCode() {
    int result = 1;
    result = 31 * result + name.hashCode();
    result = 31 * result + roomName.hashCode();
    return result;
  }
}