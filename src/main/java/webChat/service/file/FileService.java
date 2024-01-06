package webChat.service.file;

import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import webChat.dto.FileDto;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

public interface FileService {
    /**
     * 파일 업로드
     * @param file
     * @param roomId
     * @return 업로드된 파일 정보
     */
    FileDto uploadFile(MultipartFile file, String roomId);

    /**
     * roomId 하위의 모든 디렉토리/파일 삭제
     * @param roomId
     */
    void deleteFileDir(String roomId);

    // 컨트롤러에서 받아온 multipartFile 을 File 로 변환시켜서 저장하기 위한 메서드
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

    ResponseEntity<byte[]> getObject(String fileName, String filePath) throws Exception;

    void uploadFileSizeCheck(MultipartFile file);
}
