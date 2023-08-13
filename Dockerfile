### 베이스 이미지 + 이미지 별칭
#FROM adoptopenjdk:11-jdk AS builder
## 필요한 파일들 복사
#COPY gradlew build.gradle settings.gradle ./
#COPY gradle gradle/
#COPY src src/
## gradlew 실행권한 부여 및 jar 파일 생성
#RUN chmod +rwx ./gradlew && \
#    ./gradlew bootJar
## 실행 스테이지
#FROM adoptopenjdk:11-jdk
## jar 파일 복사
#COPY --from=builder build/libs/*.jar app.jar
## 컨테이너 Port 노출
#EXPOSE 8443
## jar 파일 실행
#ENTRYPOINT ["java","-jar","/app.jar"]

# adoptopenjdk:11-jdk를 기반 이미지로 사용합니다.
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
ENTRYPOINT ["java", "-Dkms.url=ws://210.220.67.85:30888/kurento", "-jar", "/app.jar"]