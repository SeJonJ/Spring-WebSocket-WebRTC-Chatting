### 구성 환경
#FROM openjdk:8-jdk-alpine
#VOLUME /tmp
### /./build/libs/Chat-0.0.1-SNAPSHOT.jar  위치에 만들어진 파일을 chatting.jar 로 복사하여 활용
#COPY ./build/libs/Chat-8.1.jar chatting.jar
#
### application.properties 포함
##ADD build/resources/main/application.properties /app/application.properties
#
### 아래 명령어로 실행
#ENTRYPOINT ["java","-jar", "chatting.jar"]

## 베이스 이미지 + 이미지 별칭
FROM openjdk:8-jdk-alpine AS builder
 # gradlew 복사
COPY gradlew .
# gradle 복사
COPY gradle gradle
# build.gradle 복사
COPY build.gradle .
# settings.gradle 복사
COPY settings.gradle .
# 웹 어플리케이션 소스 복사
COPY src src

# gradlew 실행권한 부여
RUN chmod +x ./gradlew
 # gradlew를 사용하여 실행 가능한 jar 파일 생성
RUN ./gradlew bootJar

# 베이스 이미지
FROM openjdk:8-jdk-alpine
# builder 이미지에서 build/libs/*.jar 파일을 app.jar로 복사
COPY --from=builder build/libs/*.jar app.jar

# 컨테이너 Port 노출
EXPOSE 8443

# jar 파일 실행
ENTRYPOINT ["java","-jar","/app.jar"]