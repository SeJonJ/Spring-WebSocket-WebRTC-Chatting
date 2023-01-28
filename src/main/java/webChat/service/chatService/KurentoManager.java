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

package webChat.service.chatService;

import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import webChat.dto.ChatRoomDto;
import webChat.dto.ChatRoomMap;
import webChat.dto.KurentoRoomDto;

import java.util.concurrent.ConcurrentMap;

/**
 * @modifyBy SeJon Jang (wkdtpwhs@gmail.com)
 * @Desc KuirentoRoom 을 관리하기 위한 클래스
 */
@Service
@RequiredArgsConstructor
public class KurentoManager {

  // 로깅을 위한 객체 생성
  private final Logger log = LoggerFactory.getLogger(KurentoManager.class);

  // kurento 미디어 서버 연결을 위한 객체 생성?
//  private final KurentoClient kurento;

  /**
   * @desc room 정보를 담은 map
   * */
//  private final ConcurrentMap<String, KurentoRoom> rooms = new ConcurrentHashMap<>();
  private final ConcurrentMap<String, ChatRoomDto> rooms = ChatRoomMap.getInstance().getChatRooms();

  /**
   *
   * @Desc room 정보 가져오기
   * @param roomId room 이름
   * @return 만약에 room 이 있다면 해당 room 객체 return 아니라면 새로운 room 생성 후 return
   */
  public KurentoRoomDto getRoom(String roomId) {
    log.debug("Searching for room {}", roomId);

    // roomName 기준으로 room 가져오기
    KurentoRoomDto room = (KurentoRoomDto) rooms.get(roomId);

    // room return
    return room;
  }

  /**
   *
   * @param room
   * @Desc room 삭제
   */
  public void removeRoom(KurentoRoomDto room) {
    // rooms 에서 room 객체 삭제 => 이때 room 의 Name 을 가져와서 조회 후 삭제
    this.rooms.remove(room.getRoomId());

    // room 을 종료?
    room.close();

    log.info("Room {} removed and closed", room.getRoomId());
  }

}