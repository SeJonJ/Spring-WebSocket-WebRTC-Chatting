package webChat.service;

import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileUploadRequestDto;
import webChat.dto.FileUploadResponseDto;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

public interface FileService {
    // 파일 response 를 위한 멤버 변수 정의
    FileUploadResponseDto uploadFile(FileUploadRequestDto uploadReq);

    // 현재 방에 업로드된 모든 파일 삭제
    void deleteFileDir(String path);

    // 파일 업로드를 위한 메서드
    // 정확히는 컨트롤러에서 받아온 multipartFile 을 File 로 변환시켜서 저장한 후
    // 원래 있던 임시 파일은 삭제하기 위함
    default File convertMultipartFileToFile(MultipartFile mfile, String tmpPath) throws IOException {
        File file = new File(tmpPath);

        if (file.createNewFile()) {
            try (FileOutputStream fos = new FileOutputStream(file)) {
                fos.write(mfile.getBytes());
            }
            return file;
        }
        throw new IOException();
    }

    // 파일 삭제
    default void removeFile(File file){
        file.delete();
    }
}
