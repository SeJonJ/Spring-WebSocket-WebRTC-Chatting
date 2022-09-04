package webChat.service;

import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectInputStream;
import com.amazonaws.services.s3.model.S3ObjectSummary;
import com.amazonaws.services.s3.transfer.TransferManager;
import com.amazonaws.services.s3.transfer.TransferManagerBuilder;
import com.amazonaws.services.s3.transfer.Upload;
import com.amazonaws.util.IOUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileUploadDto;

import java.io.File;
import java.io.IOException;


@Service
@RequiredArgsConstructor
@Slf4j
public class S3FileService implements FileService{

    // AmazonS3 주입받기
    private final AmazonS3 amazonS3;

    @Value("${cloud.aws.s3.bucket}")
    private String bucket;

    @Value("${cloud.aws.s3.bucket.url}")
    private String baseUrl;

    @Override
    public FileUploadDto uploadFile(MultipartFile file, String transaction, String roomId) {
        try{

            String filename = file.getOriginalFilename(); // 파일원본 이름
            String key = roomId+"/"+transaction+"/"+filename; // S3 파일 경로

            File convertedFile = convertMultipartFileToFile(file, transaction + filename);

            TransferManager transferManager = TransferManagerBuilder
                    .standard()
                    .withS3Client(amazonS3)
                    .build();

            Upload upload = transferManager.upload(bucket, key, convertedFile);
            upload.waitForUploadResult();
            removeFile(convertedFile);

            // upload 객체 빌드
            FileUploadDto uploadReq = FileUploadDto.builder()
                    .transaction(transaction)
                    .chatRoom(roomId)
                    .originFileName(filename)
                    .fileDir(key)
                    .s3DataUrl(baseUrl+"/"+key)
                    .build();

            return uploadReq;

        } catch (Exception e) {
            log.error("fileUploadException {}", e.getMessage());
            return null;
        }
    }

    @Override
    public void deleteFileDir(String path) {
        for (S3ObjectSummary summary : amazonS3.listObjects(bucket, path).getObjectSummaries()) {
            amazonS3.deleteObject(bucket, summary.getKey());
        }
    }

    @Override
    public ResponseEntity<byte[]> getObject(String fileDir, String fileName) throws IOException {
        S3Object object = amazonS3.getObject(new GetObjectRequest(bucket, fileDir));
        S3ObjectInputStream objectInputStream = object.getObjectContent();
        byte[] bytes = IOUtils.toByteArray(objectInputStream);

        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        httpHeaders.setContentDispositionFormData("attachment", fileName);

        log.info("HttpHeader : [{}]", httpHeaders);

        return new ResponseEntity<>(bytes, httpHeaders, HttpStatus.OK);
    }

}
