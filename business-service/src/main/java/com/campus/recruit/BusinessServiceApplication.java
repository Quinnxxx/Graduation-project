package com.campus.recruit;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * business-service 启动类
 *
 * <p>campus-recruit-ai-platform 核心业务后端服务，负责用户认证、用户信息管理等基础能力。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@SpringBootApplication
public class BusinessServiceApplication {

    /**
     * 应用启动入口
     *
     * @param args 启动参数
     */
    public static void main(String[] args) {
        SpringApplication.run(BusinessServiceApplication.class, args);
        log.info("business-service started successfully");
    }
}
