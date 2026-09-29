package com.campus.recruit.config;

import cn.hutool.json.JSONUtil;
import com.campus.recruit.common.Result;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * JWT 认证拦截器
 *
 * <p>拦截受保护接口，校验请求头中的 Bearer Token，并将解析出的用户信息写入 request attribute 供 Controller 使用。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Component
@RequiredArgsConstructor
public class JwtAuthInterceptor implements HandlerInterceptor {

    /** 当前登录用户 ID 的 request attribute 键 */
    public static final String ATTR_USER_ID = "userId";

    /** 当前登录用户名的 request attribute 键 */
    public static final String ATTR_USERNAME = "username";

    private final JwtUtil jwtUtil;

    /**
     * 请求前置校验：解析并校验 Token
     *
     * @param request  请求对象
     * @param response 响应对象
     * @param handler  目标处理器
     * @return 校验通过返回 true，否则返回 false
     * @throws IOException IO 异常
     */
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws IOException {
        // 仅拦截 Controller 方法，放行静态资源等
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }
        String header = request.getHeader(jwtUtil.getHeader());
        if (StringUtils.isBlank(header) || !header.startsWith(jwtUtil.getPrefix())) {
            writeUnauthorized(response);
            return false;
        }
        try {
            String token = header.substring(jwtUtil.getPrefix().length()).trim();
            Claims claims = jwtUtil.parseToken(token);
            request.setAttribute(ATTR_USER_ID, claims.get("userId", Long.class));
            request.setAttribute(ATTR_USERNAME, claims.getSubject());
            return true;
        } catch (Exception e) {
            writeUnauthorized(response);
            return false;
        }
    }

    /**
     * 写入 401 未授权响应
     *
     * @param response 响应对象
     * @throws IOException IO 异常
     */
    private void writeUnauthorized(HttpServletResponse response) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json;charset=" + StandardCharsets.UTF_8);
        response.getWriter().write(JSONUtil.toJsonStr(Result.fail(ResultCode.UNAUTHORIZED)));
    }
}
