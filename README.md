# SpringBoot WebSocket Chatting Project
[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2FSeJonJ%2FSpring-WebSocket-Chatting&count_bg=%233310C8&title_bg=%2316C86B&icon=&icon_color=%23E7E7E7&title=HITS&edge_flat=true)](https://hits.seeyoufarm.com)

## 0. Spring Boot 와 WebSocket 을 활용한 채팅 만들기 프로젝트
- SpringBoot 기반 웹 소켓 채팅 및 Kurento Media Server 를 이용한 N:M 화상채팅
- 상세한 코드 설명은  https://terianp.tistory.com/184 에서 확인 가능합니다.

### 브랜치별 설명
- master : 기본 문자 채팅
- master-Webrtc-jpa : 일반 채팅 + 실시간 화상 채팅, 화면 공유(P2P)
- master-webrtc-kurento-jpa : kurento 미디어 서버를 활용한 webrtc 화상 채팅

## 1. 사용기술
- Java 11
- Spring Boot MVC
- Gradle
- AJAX
- jquery
- WebSocket & SocketJS
- Stomp
- WebRTC : P2P 실시간 화상 채팅, 화면 공유
- Kurento Media Server : N:M 채팅을 위한 KMS 사용

## 2. 다이어그램
![Chat.png](info%2FChat.png)

## 3. 구현 기능
1) 기본 기능
   - 채팅방 생성
   - 채팅방 생성 시 중복검사
   - 채팅방 닉네임 선택 
     - 닉네임 중복 시 임의의 숫자를 더해서 중복 안되도록
   - 채팅방 입장 & 퇴장 확인
   - 채팅 기능
     - RestAPI 기반 메시지 전송/수신
   - 채팅방 유저 리스트 & 유저 숫자 확인
2) 채팅방 추가 기능
   - Amazon S3 기반으로 하는 채팅방 파일 업로드&다운로드 
     - jquery, ajax 활용
   - 채팅방 암호화 - 09.12 완료
   - 채팅방 삭제
     - ~~채팅방 삭제 시 해당 채팅방 안에 있는 파일들도 S3 에서 함께 삭제~~
   - 채팅방 유저 인원 설정
     - 인원 제한 시 제한 된 인원만 채팅 참여 가능
3) 화상채팅 기능 - WebRTC
   - WebRTC 화상 채팅 
     - P2P 기반 음성&영상 채팅, 화면 공유 기능
     - 양방향 화면 공유
  - KMS : Kurento Media Server
    - 쿠렌토 미디어 서버를 사용한 N:M 채팅
    - 양방향 화면 공유
4) 방 관리를 위한 BatchJob 및 RestfullAPI 개발

## 5. 구동방법
1) Server Installation  
- Kurento Media Server 설치  
- turn Server 설치 : coturn  
- Kurento Media Server 사용시 환경변수 설정 필요 : -Dkms.url=ws://[KMS IP]:[PORT]/kurento  

2) JAR Build
- java -Dkms.url=ws://[KMS IP]:[PORT]/kurento -jar jar파일명

3) Docker Container
- Spring 프로젝트를 Docker Image 로 만들기 위한 DockerFile
```bash
FROM adoptopenjdk:11-jdk as builder

# 작업 디렉토리를 설정합니다.
WORKDIR /workspace/app

# 프로젝트의 모든 파일을 Docker 이미지 내부로 복사합니다.
COPY . .

# Gradle을 사용하여 프로젝트를 빌드합니다.
RUN ./gradlew clean build -x test

# 런타임 이미지를 생성합니다.
FROM adoptopenjdk:11-jdk

# 3. 8443 포트를 외부로 노출합니다.
EXPOSE 8443

# 빌드된 JAR 파일을 런타임 이미지로 복사합니다.
COPY --from=builder /workspace/app/build/libs/*.jar app.jar

# Spring Boot 애플리케이션을 실행합니다.
ENTRYPOINT ["java", "-jar", "/app.jar"]
```


## 6. ChatForYou
# 230914
- 자체 서버 배포 완료!
- 현재 kurento 화상채팅을 적용한 서버 배포중입니다. 다만 아직 안정화 중이라서 자주 꺼지거나 그럴 수 있습니다
- 자체 서버를 사용하기 때문에 이전보다 조금 더 느릴 수 있습니다
- 자체 인증서를 사용하기 때문에 사이트에 문제가 있을 수 있다고 나오지만...그런 이상한 사이트 아니에요ㅠ.ㅠ  
https://hjproject.kro.kr:8653

## 7. 구동 화면

![](info/chattingFileUpload.gif)

![ChatForYou.gif](info%2FChatForYou.gif)


## Reference
https://github.com/Benkoff/WebRTC-SS

https://github.com/codejs-kr/webrtc-lab

https://doc-kurento.readthedocs.io/en/latest/index.html

## License
GNU General Public License v3.0 