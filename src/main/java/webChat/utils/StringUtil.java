package webChat.utils;

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
}