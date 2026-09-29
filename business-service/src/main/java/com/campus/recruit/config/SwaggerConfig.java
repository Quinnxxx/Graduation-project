package com.campus.recruit.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 接口文档配置（Knife4j / springdoc-openapi）
 *
 * <p>访问入口：{@code http://localhost:8080/doc.html}。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Configuration
public class SwaggerConfig {

    /** 认证方案名称 */
    private static final String SECURITY_SCHEME_NAME = "BearerAuth";

    /**
     * 构造 OpenAPI 文档信息（含 JWT 认证方案）
     *
     * @return OpenAPI 实例
     */
    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("campus-recruit-ai-platform API")
                        .description("campus-recruit-ai-platform 业务后端服务接口文档")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("campus-recruit-team")
                                .email("dev@campus-recruit.com")))
                // 全局声明 JWT 认证，接口上无需重复标注
                .addSecurityItem(new SecurityRequirement().addList(SECURITY_SCHEME_NAME))
                .components(new Components().addSecuritySchemes(SECURITY_SCHEME_NAME,
                        new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT")
                                .in(SecurityScheme.In.HEADER)
                                .name("Authorization")));
    }
}
