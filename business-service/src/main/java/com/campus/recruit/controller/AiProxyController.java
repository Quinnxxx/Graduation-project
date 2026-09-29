package com.campus.recruit.controller;

import com.campus.recruit.common.Result;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.config.AiProperties;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.AiChatDTO;
import com.campus.recruit.vo.AiChatVO;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;

/**
 * AI 服务转发接口
 *
 * <p>前端统一经本层访问 AI Agent 服务：本层负责用户 JWT 鉴权（{@code /ai/**}
 * 已被 {@code JwtAuthInterceptor} 覆盖）、从登录态注入 user_id、附加内部令牌
 * {@code X-Internal-Token}，对前端屏蔽 AI 服务内网地址与内部凭证。</p>
 *
 * <p>提供两种模式：非流式（一次性返回完整结果）与 SSE 流式（逐 token 推送
 * meta/chunk/final/error 事件）。流式转发在独立线程池中阻塞读取，避免占用
 * Tomcat 请求线程。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Tag(name = "AI 服务转发", description = "前端经本层转发 AI Agent 服务（统一鉴权 + 内部令牌）")
@RestController
@RequiredArgsConstructor
@Validated
@RequestMapping("/ai")
public class AiProxyController {

    /** AI 服务非流式对话路径 */
    private static final String PATH_CHAT = "/api/v1/agent/chat";

    /** AI 服务 SSE 流式对话路径 */
    private static final String PATH_CHAT_STREAM = "/api/v1/agent/chat/stream";

    /** SSE 数据帧前缀（与 AI 服务下发格式一致） */
    private static final String SSE_DATA_PREFIX = "data: ";

    /** AI 服务不可用时下发给前端的错误事件载荷 */
    private static final String ERROR_EVENT_UNAVAILABLE =
            "{\"type\":\"error\",\"data\":\"AI 服务不可用\"}";

    /** AI 流式转发失败时下发给前端的错误事件载荷 */
    private static final String ERROR_EVENT_PROXY_FAILED =
            "{\"type\":\"error\",\"data\":\"AI 服务转发失败\"}";

    private final AiProperties aiProperties;

    @Qualifier("aiProxyExecutor")
    private final ExecutorService aiProxyExecutor;

    /**
     * 转发专用 JSON 映射器。
     *
     * <p>采用 SNAKE_CASE 命名策略，将 AI 服务返回的 snake_case data（agent_name、
     * final_response）映射到 camelCase 的 {@link AiChatVO}；同时忽略 AI 返回中本层
     * 未声明的字段（如 intent）。该策略只作用于 POJO 属性，不影响请求体 Map 的 key
     * （Map 中已显式使用 user_id 等 snake_case 键）。</p>
     */
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

    /**
     * 组装发往 AI 服务的请求体
     *
     * <p>user_id 强制取自从当前登录用户 JWT 解析出的 attribute，覆盖任何前端传值，
     * 防止越权伪造他人身份。</p>
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @param dto     前端对话参数
     * @return snake_case 的 AI 服务请求体 Map
     */
    private Map<String, Object> buildRequestBody(HttpServletRequest request, AiChatDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        Map<String, Object> body = new HashMap<>();
        body.put("user_id", String.valueOf(userId));
        body.put("session_id", dto.getSessionId());
        body.put("query", dto.getQuery());
        body.put("resume_text", dto.getResumeText());
        return body;
    }

    /**
     * 创建 HTTP 客户端（仅设置连接超时，读取超时在每个请求上设置）
     *
     * @return JDK 原生 HttpClient
     */
    private HttpClient newClient() {
        return HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(aiProperties.getConnectTimeoutMs()))
                .build();
    }

    /**
     * 构建发往 AI 服务的 POST 请求（携带内部令牌与读取超时）
     *
     * @param path     AI 服务接口路径
     * @param jsonBody 请求体 JSON 字符串
     * @return HTTP 请求对象
     */
    private HttpRequest buildHttpRequest(String path, String jsonBody) {
        return HttpRequest.newBuilder()
                .uri(URI.create(aiProperties.getBaseUrl() + path))
                .header("Content-Type", "application/json")
                .header("X-Internal-Token", aiProperties.getInternalToken())
                .timeout(Duration.ofMillis(aiProperties.getReadTimeoutMs()))
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8))
                .build();
    }

    /**
     * AI 对话（非流式）
     *
     * <p>同步调用 AI 服务图编排接口，解包其统一响应后以本系统 {@link Result} 返回。</p>
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @param dto     对话参数
     * @return AI 对话结果视图对象
     */
    @Operation(summary = "AI 对话（非流式）")
    @PostMapping("/chat")
    public Result<AiChatVO> chat(HttpServletRequest request, @Valid @RequestBody AiChatDTO dto) {
        try {
            String jsonBody = OBJECT_MAPPER.writeValueAsString(buildRequestBody(request, dto));
            HttpResponse<String> resp = newClient().send(
                    buildHttpRequest(PATH_CHAT, jsonBody),
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (resp.statusCode() != 200) {
                log.warn("AI 非流式服务返回异常状态码: {}", resp.statusCode());
                return Result.fail(ResultCode.AI_SERVICE_ERROR.getCode(),
                        "AI 服务返回异常状态: " + resp.statusCode());
            }
            // AI 服务统一返回 {code,message,data}，code=0 表示成功
            JsonNode root = OBJECT_MAPPER.readTree(resp.body());
            if (root.path("code").asInt(-1) != 0) {
                String message = root.path("message").asText("AI 服务调用失败");
                return Result.fail(ResultCode.AI_SERVICE_ERROR.getCode(), message);
            }
            AiChatVO vo = OBJECT_MAPPER.convertValue(root.path("data"), AiChatVO.class);
            return Result.success(vo);
        } catch (Exception e) {
            log.error("AI 服务非流式转发失败", e);
            return Result.fail(ResultCode.AI_SERVICE_ERROR.getCode(), "AI 服务不可用，请稍后再试");
        }
    }

    /**
     * AI 对话（SSE 流式）
     *
     * <p>在独立线程池中阻塞读取 AI 服务的 SSE 响应，将 {@code data:} 帧原样透传给
     * 前端；请求体在提交线程池前于 Tomcat 线程构造，避免异步线程访问已回收的
     * {@link HttpServletRequest}。</p>
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @param dto     对话参数
     * @return SSE Emitter
     */
    @Operation(summary = "AI 对话（流式 SSE）")
    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(HttpServletRequest request, @Valid @RequestBody AiChatDTO dto) {
        SseEmitter emitter = new SseEmitter((long) aiProperties.getReadTimeoutMs());
        emitter.onTimeout(emitter::complete);

        // 在 Tomcat 线程完成用户身份解析与请求体序列化，异步线程不再触碰 request
        final String jsonBody;
        try {
            jsonBody = OBJECT_MAPPER.writeValueAsString(buildRequestBody(request, dto));
        } catch (Exception e) {
            log.error("AI 流式请求体构造失败", e);
            throw new IllegalArgumentException("AI 对话请求参数序列化失败", e);
        }

        aiProxyExecutor.submit(() -> {
            try {
                HttpResponse<InputStream> resp = newClient().send(
                        buildHttpRequest(PATH_CHAT_STREAM, jsonBody),
                        HttpResponse.BodyHandlers.ofInputStream());
                try (InputStream is = resp.body();
                     BufferedReader reader = new BufferedReader(
                             new InputStreamReader(is, StandardCharsets.UTF_8))) {
                    if (resp.statusCode() != 200) {
                        log.warn("AI 流式服务返回异常状态码: {}", resp.statusCode());
                        emitter.send(SseEmitter.event().data(ERROR_EVENT_UNAVAILABLE));
                    } else {
                        String line;
                        while ((line = reader.readLine()) != null) {
                            if (line.startsWith(SSE_DATA_PREFIX)) {
                                String payload = line.substring(SSE_DATA_PREFIX.length()).trim();
                                if (!payload.isEmpty()) {
                                    emitter.send(SseEmitter.event().data(payload));
                                }
                            }
                        }
                    }
                }
                emitter.complete();
            } catch (Exception e) {
                log.error("AI 流式转发失败", e);
                try {
                    emitter.send(SseEmitter.event().data(ERROR_EVENT_PROXY_FAILED));
                } catch (Exception ignored) {
                    // 客户端已断开，无法再下发错误帧
                }
                emitter.completeWithError(e);
            }
        });
        return emitter;
    }
}
