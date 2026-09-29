package com.campus.recruit.config;

import cn.hutool.core.thread.ThreadFactoryBuilder;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;

/**
 * AI 服务转发相关配置
 *
 * <p>注册 {@link AiProperties}，并提供 SSE 转发专用线程池：SSE 转发需阻塞读取
 * AI 服务的流式响应，不能占用 Tomcat 请求线程，故使用独立固定线程池承载。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Configuration
@EnableConfigurationProperties(AiProperties.class)
public class AiProxyConfig {

    /** SSE 转发线程池线程名前缀 */
    private static final String THREAD_NAME_PREFIX = "ai-proxy-";

    /** SSE 转发固定线程数 */
    private static final int PROXY_POOL_SIZE = 4;

    /**
     * SSE 转发专用线程池
     *
     * <p>使用 hutool 的 {@link ThreadFactoryBuilder} 生成带统一命名前缀的线程，
     * 便于线程栈与监控排查；容器关闭时调用 shutdown 释放线程。</p>
     *
     * @return 固定大小的线程池
     */
    @Bean(name = "aiProxyExecutor", destroyMethod = "shutdown")
    public ExecutorService aiProxyExecutor() {
        ThreadFactory threadFactory = new ThreadFactoryBuilder()
                .setNamePrefix(THREAD_NAME_PREFIX)
                .build();
        return Executors.newFixedThreadPool(PROXY_POOL_SIZE, threadFactory);
    }
}
