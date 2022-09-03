package webChat.controller;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileUploadRequestDto;
import webChat.service.S3FileService;

import java.util.UUID;

@RestController
@RequestMapping("/s3")
@Slf4j
public class FileController {

    @Autowired
    private S3FileService fileService;

    @PostMapping("/file")
    public String uploadFile(@RequestParam("file") MultipartFile file, @RequestParam("roomId")String roomId){
        FileUploadRequestDto reqDto = FileUploadRequestDto.builder()
                .file(file)
                .transaction(UUID.randomUUID().toString())
                .chatRoom(roomId)
                .build();

        log.info("넘어온 데이터 {}", reqDto);
        String s3DataUrl = fileService.uploadFile(reqDto).getS3DataUrl();
        log.info("fileUpload {}", s3DataUrl);

        return s3DataUrl;
    }
}
