package com.campus.recruit.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web MVC 配置
 *
 * <p>注册 JWT 认证拦截器，并放行登录注册与接口文档等公开路径。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final JwtAuthInterceptor jwtAuthInterceptor;
    private final InternalTokenInterceptor internalTokenInterceptor;

    /**
     * 注册拦截器并配置放行路径
     *
     * @param registry 拦截器注册表
     */
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // JWT 拦截器：保护用户接口
        registry.addInterceptor(jwtAuthInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns(
                        // 认证接口
                        "/auth/login",
                        "/auth/register",
                        // 接口文档
                        "/doc.html",
                        "/webjars/**",
                        "/v3/api-docs/**",
                        "/swagger-ui/**",
                        "/swagger-resources/**",
                        "/favicon.ico",
                        // 其他
                        "/error",
                        // 内部接口：不走用户 JWT，由 InternalTokenInterceptor 校验
                        "/internal/**",
                        // 校招岗位查询：公开接口，无需登录
                        "/jobs/**");
        
        // 内部令牌拦截器：保护 /internal/** 接口
        registry.addInterceptor(internalTokenInterceptor)
                .addPathPatterns("/internal/**");
    }
}
