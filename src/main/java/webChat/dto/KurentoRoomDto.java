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
import com.sun.istack.NotNull;
import lombok.*;
import org.kurento.client.Continuation;
import org.kurento.client.KurentoClient;
import org.kurento.client.MediaPipeline;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.socket.WebSocketSession;
import webChat.rtc.KurentoUserSession;

import javax.annotation.PreDestroy;
import java.io.Closeable;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.concurrent.ConcurrentMap;

/**
 * @modifyBy SeJon Jang (wkdtpwhs@gmail.com)
 * @desc 화상채팅을 위한 클래스 ChatRoomDto 를 상속받음
 */
@Getter
@Setter
@NoArgsConstructor
@RequiredArgsConstructor
public class KurentoRoomDto extends ChatRoomDto implements Closeable {

  // 로깅 객체 생성
  private final Logger log = LoggerFactory.getLogger(KurentoRoomDto.class);

  private KurentoClient kurento;

  // 미디어 파이프라인
  private MediaPipeline pipeline;

  @NotNull
  private String roomId; // 채팅방 아이디
  private String roomName; // 채팅방 이름
  private int userCount; // 채팅방 인원수
  private int maxUserCnt; // 채팅방 최대 인원 제한

  private String roomPwd; // 채팅방 삭제시 필요한 pwd
  private boolean secretChk; // 채팅방 잠금 여부
  private ChatType chatType; //  채팅 타입 여부

  /**
   * @desc 참여자를 저장하기 위한 Map
   * TODO ConcurrentHashMap 에 대해서도 공부해둘 것!
   * */
  private ConcurrentMap<String, KurentoUserSession> participants;


//  // 채팅룸 이름?
//  private final String roomId;

  // 룸 정보 set
  public void setRoomInfo(String roomId, String roomName, String roomPwd, boolean secure, int userCount, int maxUserCnt, ChatType chatType, KurentoClient kurento){
    this.roomId = roomId;
    this.roomName = roomName;
    this.roomPwd = roomPwd;
    this.secretChk = secure;
    this.userCount = userCount;
    this.maxUserCnt = maxUserCnt;
    this.chatType = chatType;
    this.kurento = kurento;
    this.participants = (ConcurrentMap<String, KurentoUserSession>) this.userList;
  }

  // 유저명 가져오기
  public String getRoomId() {
    return roomId;
  }

  /**
   * @Param roomName, pipline
   * @desc roomName 과 pipline 을 이용한 생성자
   * */
//  public KurentoRoom(String roomId, MediaPipeline pipeline) {
//    this.roomId = roomId;
//    this.pipeline = pipeline;
//    log.info("ROOM {} has been created", roomId);
//  }

  // 생성자 대신 아래 메서드로 pipline 초기화
  public void createPipline(){
    this.pipeline = this.kurento.createMediaPipeline();
//    log.info("pipline : {} ",this.pipeline);
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
  public Collection<KurentoUserSession> getParticipants() {
    return participants.values();
  }

  public KurentoUserSession getParticipant(String name) {
    return participants.get(name);
  }

  /**
   * @desc 유저가 room 에 join 할때 사용
   * @Param String userName, WebSocketSession session
   * @return UserSession 객체
   * */
  public KurentoUserSession join(String userName, WebSocketSession session) throws IOException {

    log.info("ROOM {}: adding participant {}", this.roomId, userName);

    // UserSession 은 유저명, room명, 유저 세션정보, pipline 파라미터로 받음
    final KurentoUserSession participant = new KurentoUserSession(userName, this.roomId, session, this.pipeline);

    //
    joinRoom(participant);

    // 참여자 map 에 유저명과 유저에 관한 정보를 갖는 userSession 객체를 저장
    participants.put(participant.getName(), participant);

    // 참여자 정보를 기존 참여자들에게 알림?
    sendParticipantNames(participant);

    // 방에 참여한 사람 수 +1
    userCount++;


    // 참여자 정보 return
    return participant;
  }

  public void leave(KurentoUserSession user) throws IOException {
    log.debug("PARTICIPANT {}: Leaving room {}", user.getName(), this.roomId);
    this.removeParticipant(user.getName());

    log.info("PARTICIPANTS {} ", this.participants);

    user.close();
  }

  /**
   * @Desc userSession 을 room 에 저장하기 위한 메서드
   * @Param UserSession newParticipant => 새로운 유저
   * @Return List<String 유저명>
   * */
  private Collection<String> joinRoom(KurentoUserSession newParticipant) throws IOException {
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
    log.debug("ROOM {}: 다른 참여자들에게 새로운 참여자가 들어왔음을 알림 {}", roomId,
            newParticipant.getName());

    // participants 의 value 로 for 문 돌림
    for (final KurentoUserSession participant : participants.values()) {
      try {
        // 현재 방의 모든 참여자들에게 새로운 참여자가 입장해서 만들어지는 json 객체
        // 즉, newParticipantMsg 를 send함
        participant.sendMessage(newParticipantMsg);
      } catch (final IOException e) {
        log.debug("ROOM {}: participant {} could not be notified", roomId, participant.getName(), e);
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

    log.debug("ROOM {}: notifying all users that {} is leaving the room", this.roomId, name);

    // String list 생성
    final List<String> unNotifiedParticipants = new ArrayList<>();

    // json 객체 생성
    final JsonObject participantLeftJson = new JsonObject();

    // json 객체에 유저가 떠났음을 알리는 jsonObject
    // newParticipantMsg : { "id" : "participantLeft", "name" : "참여자 유저명"}
    participantLeftJson.addProperty("id", "participantLeft");
    participantLeftJson.addProperty("name", name);

    // participants 의 value 로 for 문 돌림
    for (final KurentoUserSession participant : participants.values()) {
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
      log.debug("ROOM {}: The users {} could not be notified that {} left the room", this.roomId,
          unNotifiedParticipants, name);
    }

  }

  /**
   * @Desc 새로운 참여자 있음을 기존 참여자에게 알림
   * @Param UserSession 유저
   * @Return none
   * */
  public void sendParticipantNames(KurentoUserSession user) throws IOException {
    // jsonArray 객체 생성
    final JsonArray participantsArray = new JsonArray();

    // participants 의 value 만 return 받아서 => this.getParticipants() for 문 돌림
    for (final KurentoUserSession participant : this.getParticipants()) {
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
    for (final KurentoUserSession user : participants.values()) {
      try {
        // 유저 close
        user.close();
      } catch (IOException e) {
        log.debug("ROOM {}: Could not invoke close on participant {}", this.roomId, user.getName(),
                e);
      }
    } // for 문 끝

    // 유저 정보를 담은 map - participants - 초기화
    participants.clear();

    /** 여기서 부터는 Kurento 의 메서드 인 듯 **/
    pipeline.release(new Continuation<Void>() {

      @Override
      public void onSuccess(Void result) throws Exception {
        log.trace("ROOM {}: Released Pipeline", KurentoRoomDto.this.roomId);
      }

      @Override
      public void onError(Throwable cause) throws Exception {
        log.warn("PARTICIPANT {}: Could not release Pipeline", KurentoRoomDto.this.roomId);
      }
    });

    log.debug("Room {} closed", this.roomId);
  }

}
