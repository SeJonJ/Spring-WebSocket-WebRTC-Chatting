package webChat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class FileUploadDto {

    private String fileName;
    private String originFileName; // 파일 원본 이름
    private String roomId; // 파일이 올라간 채팅방 ID
    private String filePath; // UUID 를 활용한 랜덤한 파일 위치
    private String minioDataUrl; // 파일 링크

}
