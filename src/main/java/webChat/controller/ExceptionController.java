package webChat.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.client.HttpServerErrorException;
import javax.servlet.http.HttpServletRequest;
import java.net.UnknownHostException;
import java.util.HashMap;
import java.util.Map;

@ControllerAdvice
public class ExceptionController {

    private static final Logger log = LoggerFactory.getLogger(ExceptionController.class);

    // 권한이 없는 경우 발생하는 예외 핸들러
    @ResponseStatus(HttpStatus.UNAUTHORIZED)  // 401 status code :: 권한없음
    @ExceptionHandler(UnauthorizedException.class)
    @ResponseBody
    public Map<String, String> unauthorizedException(Exception e) {
        log.error("error :: "+e.getMessage());
        log.error("error trace :: "+e.getCause());

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
        log.error("error :: "+e.getMessage());
        log.error("error trace :: "+e.getCause());

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
    @ExceptionHandler(HttpServerErrorException.InternalServerError.class)
    @ResponseBody
    public Map<String, String> interalServerError(Exception e){
        e.printStackTrace();

        Map<String, String> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", e.getMessage());

        return result;
    }

    // 서버 에러 발생 시 예외 핸들러
    public static class InternalServerError extends RuntimeException {
        public InternalServerError(String message) {
            super(message);
        }
    }

    // 요청한 자원이 없는 경우 발생하는 예외 핸들러
    @ResponseStatus(HttpStatus.NOT_FOUND) // 404 status code
    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseBody
    public Map<String, String> resourceNotFoundException(Exception e) {
        log.error("error :: "+e.getMessage());
        log.error("error trace :: "+e.getCause());

        Map<String, String> result = new HashMap<>();
        result.put("code", "403");
        result.put("message", "there is no resource");
        return result;
    }

    // 요청한 자원이 없을 때 발생하는 커스텀 예외
    public static class ResourceNotFoundException extends RuntimeException {
        public ResourceNotFoundException(String message) {
            super(message);
        }
    }

    /**
     * 403 forbidden 발생 시 예외처리
     * @param ex
     * @param request
     * @return
     */
    @ExceptionHandler({AccessForbiddenException.class, AccessDeniedException.class, UnknownHostException.class})
    public String handleAccessException(Exception ex, HttpServletRequest request) {
        ex.printStackTrace();
        request.setAttribute("error_message", ex.getMessage());
        return "error/403"; // 403 에러 페이지로 리디렉션
    }

    public static class AccessForbiddenException extends RuntimeException {
        public AccessForbiddenException(String message) {
            super(message);
        }
    }

    //
    public static class AccessDeniedException extends RuntimeException {
        public AccessDeniedException(String message) {
            super(message);
        }
    }
}
