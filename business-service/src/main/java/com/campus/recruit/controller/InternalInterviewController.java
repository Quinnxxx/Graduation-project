package com.campus.recruit.controller;

import com.campus.recruit.common.Result;
import com.campus.recruit.service.InterviewRecordService;
import com.campus.recruit.vo.InterviewVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 模拟面试内部查询接口（AI Agent 服务专用）。
 *
 * <p>供 AI 服务在 Redis 短期记忆失效（跨天 / 服务重启）后，按面试 ID 拉取已持久化的
 * 面试详情与全部问答，用于重建短期记忆、恢复面试场景。</p>
 *
 * <p>安全：调用方必须携带正确的 {@code X-Internal-Token}；同时显式传入 {@code userId}，
 * 服务层 {@code getDetail(userId, id)} 内部校验记录归属，防止拉取他人面试。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Tag(name = "内部面试查询", description = "AI 服务重建面试记忆专用（内部令牌 + 归属校验）")
@RestController
@RequiredArgsConstructor
@Validated
@RequestMapping("/internal")
public class InternalInterviewController {

    private final InterviewRecordService interviewRecordService;

    /**
     * 查询面试详情（含全部消息，按创建时间正序）。
     *
     * @param id     面试记录 ID
     * @param userId 归属用户 ID（服务层据此校验归属，不一致抛业务异常）
     * @return 面试视图对象（interviewType / status / messages 等）
     */
    @Operation(summary = "内部查询面试详情（含消息）")
    @GetMapping("/interviews/{id}")
    public Result<InterviewVO> getInterviewDetail(
            @PathVariable("id") @NotNull @Positive Long id,
            @RequestParam("userId") @NotNull @Positive Long userId) {
        return Result.success(interviewRecordService.getDetail(userId, id));
    }
}
