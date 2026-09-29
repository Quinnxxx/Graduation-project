package com.campus.recruit.config;

import com.campus.recruit.common.Result;
import com.campus.recruit.common.ResultCode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * 内部接口令牌鉴权拦截器
 *
 * <p>对 {@code /internal/**} 路径生效，校验 {@code X-Internal-Token} 请求头。
 * 使用 constant-time 比对（{@link MessageDigest#isEqual}）防时序侧信道攻击。</p>
 *
 * <p>缺失 / 错误令牌统一返回 HTTP 401 + {@code Result.fail(TOKEN_INVALID)}。</p>
 *
 * @author campus-recruit
 * @since 1.1.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class InternalTokenInterceptor implements HandlerInterceptor {

    /** 内部令牌请求头名（与 AI 服务约定一致） */
    private static final String HEADER_INTERNAL_TOKEN = "X-Internal-Token";

    private final AiProperties aiProperties;
    private final ObjectMapper objectMapper;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String token = request.getHeader(HEADER_INTERNAL_TOKEN);
        
        if (token == null
                || !MessageDigest.isEqual(
                        token.getBytes(StandardCharsets.UTF_8),
                        aiProperties.getInternalToken().getBytes(StandardCharsets.UTF_8))) {
            log.warn("内部令牌校验失败: path={}, token={}", request.getRequestURI(), 
                    token == null ? "missing" : "***");
            
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(objectMapper.writeValueAsString(
                    Result.fail(ResultCode.TOKEN_INVALID.getCode(), "内部令牌无效")));
            return false;
        }
        
        return true;
    }
}
