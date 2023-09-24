package webChat.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import java.util.HashMap;
import java.util.Map;

@ControllerAdvice
public class ExceptionController {

    // 권한이 없는 경우 발생하는 예외 핸들러
    @ResponseStatus(HttpStatus.UNAUTHORIZED)  // 401 status code :: 권한없음
    @ExceptionHandler(UnauthorizedException.class)
    @ResponseBody
    public Map<String, String> unauthorizedException(Exception e) {

        Map<String, String> result = new HashMap<>();
        result.put("code", "401");
        result.put("message", "You Have No Authentication");
        return result;
    }

    // 권한이 없을 때 발생하는 커스텀 예외
    public static class UnauthorizedException extends RuntimeException {
        public UnauthorizedException(String message) {
            super(message);
        }
    }



    // 잘못된 요청을 받았을 경우 발생하는 예외 핸들러
    @ResponseStatus(HttpStatus.BAD_REQUEST) // 400 status code
    @ExceptionHandler(MissingRequestHeaderException.class)
    @ResponseBody
    public Map<String, String> missingHeaderException(Exception e) {
        Map<String, String> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", "Required header is missing :: " + e.getMessage());

        return result;
    }

    // 잘못된 요청을 받았을 때 발생하는 커스텀 예외
    public static class BadRequestException extends RuntimeException {
        public BadRequestException(String message) {
            super(message);
        }
    }

    // 500 서버에러
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public Map<String, String> interalServerError(Exception e){
        Map<String, String> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", e.getMessage());

        return result;
    }

    // 잘못된 요청을 받았을 때 발생하는 커스텀 예외
    public static class InternalServerError extends RuntimeException {
        public InternalServerError(String message) {
            super(message);
        }
    }

    // 요청한 자원이 없는 경우 발생하는 예외 핸들러
    /*
    @ResponseStatus(HttpStatus.NOT_FOUND) // 404 status code
    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseBody
    public String resourceNotFoundException(Exception e) {
        return e.getMessage();
    }
    */

    // 요청한 자원이 없을 때 발생하는 커스텀 예외
    /*
    public static class ResourceNotFoundException extends RuntimeException {
        public ResourceNotFoundException(String message) {
            super(message);
        }
    }
    */
}
