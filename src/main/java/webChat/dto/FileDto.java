package webChat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class FileDto {

    private String fileName;  // 파일 원본 이름
    private String roomId; // 파일이 올라간 채팅방 ID
    private String filePath; // 파일 fullpath
    private String minioDataUrl; // 파일 링크
    private String contentType;
    private Status status;

    public enum Status {
        UPLOADED, FAIL
    }

}
