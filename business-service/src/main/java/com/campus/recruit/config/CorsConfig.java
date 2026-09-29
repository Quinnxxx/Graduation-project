package com.campus.recruit.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置
 *
 * <p>允许前端（Vue3）跨域访问后端接口。生产环境建议将 allowedOriginPatterns 收敛为具体域名。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    /**
     * 配置全局跨域规则
     *
     * @param registry 跨域注册表
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
