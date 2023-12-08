package webChat.service.file.impl;

import io.minio.GetPresignedObjectUrlArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.http.Method;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import webChat.config.MinioConfig;
import webChat.dto.FileUploadDto;
import webChat.service.file.FileService;
import javax.annotation.PostConstruct;
import java.io.IOException;
import java.util.concurrent.TimeUnit;


@Service
@RequiredArgsConstructor
@Slf4j
public class MinioFileServiceImpl implements FileService {

    private final MinioConfig minioConfig;
    private MinioClient minioClient;

    @PostConstruct
    private void initMinioClient() {
        minioClient = MinioClient.builder()
                .endpoint(minioConfig.getUrl())
                .credentials(minioConfig.getAccessKey(), minioConfig.getSecretKey())
                .build();
    }

    // MultipartFile 과 transcation, roomId 를 전달받는다.
    // 이때 transcation 는 파일 이름 중복 방지를 위한 UUID 를 의미한다.
    @Override
    public FileUploadDto uploadFile(MultipartFile file, String path, String roomId) {
        String originFileName = file.getOriginalFilename();
        String fullPath = roomId+"/"+path+"/"+originFileName;

        try {
            PutObjectArgs args = PutObjectArgs.builder()
                    .bucket(minioConfig.getBucketName())
                    .object(fullPath)
                    .stream(file.getInputStream(), file.getSize(), -1)
                    .contentType(file.getContentType())
                    .build();

            minioClient.ignoreCertCheck();
            minioClient.putObject(args);

            String url = minioClient.getPresignedObjectUrl(
                    GetPresignedObjectUrlArgs.builder()
                            .method(Method.GET)
                            .bucket(minioConfig.getBucketName())
                            .object(fullPath)
                            .expiry(10, TimeUnit.MINUTES)
                            .build());

            // uploadDTO 객체 리턴
            return new FileUploadDto().builder()
                    .fileName(file.getName())
                    .originFileName(originFileName)
                    .roomId(roomId)
                    .filePath(fullPath)
                    .minioDataUrl(url)
                    .build();

        } catch (Exception e) {
            log.error("fileUploadException {}", e.getMessage());
            return null;
        }
    }

    // path 아래있는 모든 파일을 삭제한다.
    // 이때 path 는 roomId 가 된다 => S3 에 roomId/변경된 파일명(uuid)/원본 파일명 으로 되어있기 때문에
    // roomId 를 적어주면 기준이 되는 roomId 아래의 모든 파일이 삭제된다.
    @Override
    public void deleteFileDir(String path) {

    }

    // byte 배열 타입을 return 한다.
    @Override
    public ResponseEntity<byte[]> getObject(String fileDir, String fileName) throws IOException {
        // bucket 와 fileDir 을 사용해서 S3 에 있는 객체 - object - 를 가져온다.
//        S3Object object = amazonS3.getObject(new GetObjectRequest(bucket, fileDir));

        // object 를 S3ObjectInputStream 형태로 변환한다.
//        S3ObjectInputStream objectInputStream = object.getObjectContent();

        // 이후 다시 byte 배열 형태로 변환한다.
        // 아마도 파일 전송을 위해서는 다시 byte[] 즉, binary 로 변환해서 전달해야햐기 때문
//        byte[] bytes = IOUtils.toByteArray(objectInputStream);

        // 여기는 httpHeader 에 파일 다운로드 요청을 하기 위한내용
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.setContentType(MediaType.APPLICATION_OCTET_STREAM);

        // 지정된 fileName 으로 파일이 다운로드 된다.
        httpHeaders.setContentDispositionFormData("attachment", fileName);

        log.info("HttpHeader : [{}]", httpHeaders);

        // 최종적으로 ResponseEntity 객체를 리턴하는데
        // --> ResponseEntity 란?
        // ResponseEntity 는 사용자의 httpRequest 에 대한 응답 테이터를 포함하는 클래스이다.
        // 단순히 body 에 데이터를 포함하는 것이 아니라, header 와 httpStatus 까지 넣어 줄 수 있다.
        // 이를 통해서 header 에 따라서 다른 동작을 가능하게 할 수 있다 => 파일 다운로드!!

        // 나는 object가 변환된 byte 데이터, httpHeader 와 HttpStatus 가 포함된다.
//        return new ResponseEntity<>(bytes, httpHeaders, HttpStatus.OK);
        return null;
    }

}
