package webChat.utils;

import org.springframework.web.multipart.MultipartFile;

import java.util.Objects;

public class StringUtil {

    public static String nullToEmptyString(String value) {
        return value != null ? value : "";
    }

    public static Boolean isNullOrEmpty(String value){
        if (Objects.isNull(value) || "".equals(value)) {
            return true;
        }
        return false;
    }

    /**
     * 파일 확장자 가져오기
     * @param file
     * @return
     */
    public static String getExtension(MultipartFile file) {
        String fileName = file.getOriginalFilename();
        String extension = fileName.substring(fileName.lastIndexOf(".") + 1);
        return extension;
    }
}