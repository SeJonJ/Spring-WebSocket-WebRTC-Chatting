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

package webChat.dto;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import org.kurento.client.Continuation;
import org.kurento.client.MediaPipeline;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.socket.WebSocketSession;
import webChat.rtc.UserSession_Kurento;

import javax.annotation.PreDestroy;
import java.io.Closeable;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * @author Ivan Gracia (izanmail@gmail.com)
 * @since 4.3.1
 */
public class Room_Kurento implements Closeable {
  // 로깅 객체 생성
  private final Logger log = LoggerFactory.getLogger(Room_Kurento.class);

  /**
   * @desc 참여자를 저장하기 위한 Map
   * */
  private final ConcurrentMap<String, UserSession_Kurento> participants = new ConcurrentHashMap<>();

  // 미디어 파이프라인
  private final MediaPipeline pipeline;

  // 유저명?
  private final String name;

  // 유저명 가져오기
  public String getName() {
    return name;
  }

  /**
   * @Param roomName, pipline
   * @desc roomName 과 pipline 을 이용한 생성자
   * */
  public Room_Kurento(String roomName, MediaPipeline pipeline) {
    this.name = roomName;
    this.pipeline = pipeline;
    log.info("ROOM {} has been created", roomName);
  }

  /**
   * @desc 종료시 실행?
   * */
  @PreDestroy
  private void shutdown() {
    this.close();
  }

  /**
   * @Desc participants 의 value 만 return
   * */
  public Collection<UserSession_Kurento> getParticipants() {
    return participants.values();
  }

  public UserSession_Kurento getParticipant(String name) {
    return participants.get(name);
  }

  /**
   * @desc 유저가 room 에 join 할때 사용
   * @Param String userName, WebSocketSession session
   * @return UserSession 객체
   * */
  public UserSession_Kurento join(String userName, WebSocketSession session) throws IOException {

    log.info("ROOM {}: adding participant {}", this.name, userName);

    // UserSession 은 유저명, room명, 유저 세션정보, pipline 파라미터로 받음
    final UserSession_Kurento participant = new UserSession_Kurento(userName, this.name, session, this.pipeline);

    //
    joinRoom(participant);

    // 참여자 map 에 유저명과 유저에 관한 정보를 갖는 userSession 객체를 저장
    participants.put(participant.getName(), participant);

    // 참여자 정보를
    sendParticipantNames(participant);

    // 참여자 정보 return
    return participant;
  }

  public void leave(UserSession_Kurento user) throws IOException {
    log.debug("PARTICIPANT {}: Leaving room {}", user.getName(), this.name);
    this.removeParticipant(user.getName());
    user.close();
  }

  /**
   * @Desc userSession 을 room 에 저장하기 위한 메서드
   * @Param UserSession newParticipant => 새로운 유저
   * @Return List<String 유저명>
   * */
  private Collection<String> joinRoom(UserSession_Kurento newParticipant) throws IOException {
    // JsonObject 를 생성
    final JsonObject newParticipantMsg = new JsonObject();

    // 유저가 참여했음을 알리는 jsonObject
    // newParticipantMsg : { "id" : "newParticipantArrived", "name" : "참여자 유저명"}
    newParticipantMsg.addProperty("id", "newParticipantArrived");
    newParticipantMsg.addProperty("name", newParticipant.getName());

    // participants 를 list 형태로 변환 => 이때 list 는 한명의 유저가 새로 들어올 때마다
    // 즉 joinRoom 이 실행될 때마다 새로 생성 && return 됨
    final List<String> participantsList = new ArrayList<>(participants.values().size());
//    log.debug("ROOM {}: notifying other participants of new participant {}", name,
//        newParticipant.getName());
    log.debug("ROOM {}: 다른 참여자들에게 새로운 참여자가 들어왔음을 알림 {}", name,
            newParticipant.getName());

    // participants 의 value 로 for 문 돌림
    for (final UserSession_Kurento participant : participants.values()) {
      try {
        // 현재 방의 모든 참여자들에게 새로운 참여자가 입장해서 만들어지는 json 객체
        // 즉, newParticipantMsg 를 send함
        participant.sendMessage(newParticipantMsg);
      } catch (final IOException e) {
        log.debug("ROOM {}: participant {} could not be notified", name, participant.getName(), e);
      }

      // list 에 유저명 추가
      participantsList.add(participant.getName());
    }

    // 유저 리스트를 return
    return participantsList;
  }

  /**
   * @Desc 유저가 제거되었을 때 이벤트 처리 => 즉 유저가 방에서 나갔을 때 이벤트 처리
   * @Param String name
   * @Return none
   * */
  private void removeParticipant(String name) throws IOException {

    // participants map 에서 제거된 유저 - 방에서 나간 유저 - 를 제거함
    participants.remove(name);

    log.debug("ROOM {}: notifying all users that {} is leaving the room", this.name, name);

    // String list 생성
    final List<String> unNotifiedParticipants = new ArrayList<>();

    // json 객체 생성
    final JsonObject participantLeftJson = new JsonObject();

    // json 객체에 유저가 떠났음을 알리는 jsonObject
    // newParticipantMsg : { "id" : "participantLeft", "name" : "참여자 유저명"}
    participantLeftJson.addProperty("id", "participantLeft");
    participantLeftJson.addProperty("name", name);

    // participants 의 value 로 for 문 돌림
    for (final UserSession_Kurento participant : participants.values()) {
      try {
        // 나간 유저의 video 를 cancel 하기 위한 메서드
        participant.cancelVideoFrom(name);

        // 다른 유저들에게 현재 유저가 나갔음을 알리는 jsonMsg 를 전달
        participant.sendMessage(participantLeftJson);

      } catch (final IOException e) {
        unNotifiedParticipants.add(participant.getName());
      }
    }

    // 만약 unNotifiedParticipants 가 비어있지 않다면
    if (!unNotifiedParticipants.isEmpty()) {
      log.debug("ROOM {}: The users {} could not be notified that {} left the room", this.name,
          unNotifiedParticipants, name);
    }

  }

  /**
   * @Desc
   * @Param UserSession 유저
   * @Return none
   * */
  public void sendParticipantNames(UserSession_Kurento user) throws IOException {
    // jsonArray 객체 생성
    final JsonArray participantsArray = new JsonArray();

    // participants 의 value 만 return 받아서 => this.getParticipants() for 문 돌림
    for (final UserSession_Kurento participant : this.getParticipants()) {
      // 만약 참여자의 정보가 파라미터로 넘어온 user 와 같지 않다면
      if (!participant.equals(user)) {
        // TODO 여기는 추가 정리
        final JsonElement participantName = new JsonPrimitive(participant.getName());
        participantsArray.add(participantName);
      }
    }

    // json 오브젝트 생성
    final JsonObject existingParticipantsMsg = new JsonObject();

    // 현재 존재하는 참여자들에 대한 정보를 담는 json Msg 생성
    // id : existingParticipants
    // data : 현재 방 안에 존재하는 유저만을 담은 array
    existingParticipantsMsg.addProperty("id", "existingParticipants");
    existingParticipantsMsg.add("data", participantsArray);
    log.debug("PARTICIPANT {}: sending a list of {} participants", user.getName(),
        participantsArray.size());

    // user 에게 existingParticipantsMsg 전달
    user.sendMessage(existingParticipantsMsg);
  }

  // 방이 close 되었을 때 사용됨?
  // 이건 실제로 찍어봐야 알 듯
  @Override
  public void close() {
    // participants 의 value 값으로 for 문 시작
    for (final UserSession_Kurento user : participants.values()) {
      try {
        // 유저 close
        user.close();
      } catch (IOException e) {
        log.debug("ROOM {}: Could not invoke close on participant {}", this.name, user.getName(),
                e);
      }
    } // for 문 끝

    // 유저 정보를 담은 map - participants - 초기화
    participants.clear();

    /** 여기서 부터는 Kurento 의 메서드 인 듯 **/
    pipeline.release(new Continuation<Void>() {

      @Override
      public void onSuccess(Void result) throws Exception {
        log.trace("ROOM {}: Released Pipeline", Room_Kurento.this.name);
      }

      @Override
      public void onError(Throwable cause) throws Exception {
        log.warn("PARTICIPANT {}: Could not release Pipeline", Room_Kurento.this.name);
      }
    });

    log.debug("Room {} closed", this.name);
  }

}
