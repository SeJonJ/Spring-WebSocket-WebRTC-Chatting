package webChat.config;

import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * cache 어노테이션을 사용해서 데이터를 cache 에 저장해 둔 후 가져오기 위한 클래스
 * 추후 @Cacheable 대신 redis 로 변경 예정
 */
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager() {
        return new ConcurrentMapCacheManager("blackList");
    }
}
