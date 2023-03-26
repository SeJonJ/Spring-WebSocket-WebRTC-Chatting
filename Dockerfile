## 베이스 이미지 + 이미지 별칭
FROM --platform=linux/amd64 adoptopenjdk:11-jdk-hotspot AS builder

# 환경변수 설정
#ENV GRADLE_USER_HOME /gradle_cache

#### option 1. 기본 도커 이미지 빌드, 직접 bootJar 실행해야함
## bootJar 로 만들어진 jar 파일을 chatting.jar 로 복사하여 활용
COPY ./build/libs/Chat-9.0.jar chatting.jar

##### option 2. 도커 이미지 빌드하면서 알아서 bootJar 실행하고 알아서 다 해줌
## gradlew 복사
#COPY gradlew .
## gradle 복사
#COPY gradle gradle
## build.gradle 복사
#COPY build.gradle .
## settings.gradle 복사
#COPY settings.gradle .
## 웹 어플리케이션 소스 복사
#COPY src src
#
### gradlew 실행권한 부여
#RUN chmod +rwx ./gradlew
### gradlew를 사용하여 실행 가능한 jar 파일 생성
#RUN ./gradlew bootJar
#
## 베이스 이미지
#FROM adoptopenjdk:11-jdk-hotspot
## builder 이미지에서 build/libs/*.jar 파일을 app.jar로 복사
#COPY --from=builder build/libs/*.jar chatting.jar

# 컨테이너 Port 노출
EXPOSE 8443

# jar 파일 실행
ENTRYPOINT ["java", "-jar", "chatting.jar"]