package com.campus.recruit.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * AI Agent 服务转发配置
 *
 * <p>对应 application.yml 中 {@code ai.service.*} 配置项，由
 * {@link AiProxyConfig} 通过 {@code @EnableConfigurationProperties} 注册。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@ConfigurationProperties(prefix = "ai.service")
public class AiProperties {

    /** AI 服务基础地址，如 http://localhost:8001 */
    private String baseUrl;

    /** 内部访问令牌（须与 AI 服务的 AI_INTERNAL_TOKEN 一致） */
    private String internalToken;

    /** 连接超时（毫秒） */
    private int connectTimeoutMs = 3000;

    /** 读取超时（毫秒）：AI 深度推理单次可达 2 分钟以上，默认 5 分钟 */
    private int readTimeoutMs = 300000;
}
