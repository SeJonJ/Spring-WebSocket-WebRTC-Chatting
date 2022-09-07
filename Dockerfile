## 구성 환경
FROM openjdk:8-jdk-alpine
VOLUME /tmp
## /./build/libs/Chat-0.0.1-SNAPSHOT.jar  위치에 만들어진 파일을 chatting.jar 로 복사하여 활용
COPY ./build/libs/Chat-0.0.1-SNAPSHOT.jar chatting.jar
## 아래 명령어로 실행
ENTRYPOINT ["java","-jar","chatting.jar"]
