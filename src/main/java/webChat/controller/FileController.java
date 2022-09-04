package webChat.controller;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileUploadDto;
import webChat.service.S3FileService;

import java.io.IOException;
import java.util.UUID;

@RestController
@RequestMapping("/s3")
@Slf4j
public class FileController {

    @Autowired
    private S3FileService fileService;

    @PostMapping("/upload")
    public FileUploadDto uploadFile(@RequestParam("file") MultipartFile file, @RequestParam("roomId")String roomId){

        FileUploadDto fileReq = fileService.uploadFile(file, UUID.randomUUID().toString(), roomId);
        log.info("최종 upload Data {}", fileReq);

        return fileReq;
    }

    @GetMapping("/download/{fileName}")
    public ResponseEntity<byte[]> download(@PathVariable String fileName, @RequestParam("fileDir")String fileDir){
        log.info("fileDir : fileName [{} : {}]", fileDir, fileName);
        try {
            return fileService.getObject(fileDir, fileName);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

}
