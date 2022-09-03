package webChat.service;

import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.model.S3ObjectSummary;
import com.amazonaws.services.s3.transfer.TransferManager;
import com.amazonaws.services.s3.transfer.TransferManagerBuilder;
import com.amazonaws.services.s3.transfer.Upload;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.tomcat.util.http.fileupload.FileUploadException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileUploadRequestDto;
import webChat.dto.FileUploadResponseDto;

import java.io.File;


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
    public FileUploadResponseDto uploadFile(FileUploadRequestDto uploadReq) {
        try{
            MultipartFile file = uploadReq.getFile();

            String transaction = uploadReq.getTransaction();

            String filename = uploadReq.getFile().getOriginalFilename();
            String key = uploadReq.getChatRoom()+"/"+transaction+"/"+filename;

            File convertedFile = convertMultipartFileToFile(file, transaction + filename);

            TransferManager transferManager = TransferManagerBuilder
                    .standard()
                    .withS3Client(amazonS3)
                    .build();

            Upload upload = transferManager.upload(bucket, key, convertedFile);
            upload.waitForUploadResult();
            removeFile(convertedFile);

            return new FileUploadResponseDto(baseUrl+"/"+key);

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

}
