package webChat.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Optional;


@Service
public class Parser {
    private final Logger logger = LoggerFactory.getLogger(this.getClass());


    public Optional<Long> parseId(String sId) {
        Long id = null;

        try {
            id = Long.valueOf(sId);
        } catch (Exception e) {
            logger.debug("에러 발생!! : {}", e.getMessage());
        }

        return Optional.ofNullable(id);
    }
}
