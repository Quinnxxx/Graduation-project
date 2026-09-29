package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.SessionCreateDTO;
import com.campus.recruit.dto.SessionQueryDTO;
import com.campus.recruit.dto.SessionUpdateDTO;
import com.campus.recruit.service.SessionRecordService;
import com.campus.recruit.vo.SessionVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户会话接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "用户会话", description = "用户任务会话记录管理与查询")
@RestController
@RequiredArgsConstructor
@Validated
public class SessionRecordController {

    private final SessionRecordService sessionRecordService;

    /**
     * 创建用户会话
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     创建参数
     * @return 会话视图对象
     */
    @Operation(summary = "创建用户会话")
    @PostMapping("/sessions")
    public Result<SessionVO> create(HttpServletRequest request, @Valid @RequestBody SessionCreateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(sessionRecordService.create(userId, dto));
    }

    /**
     * 分页查询我的会话记录
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     分页参数（GET 查询参数）
     * @return 分页结果
     */
    @Operation(summary = "分页查询我的会话记录")
    @GetMapping("/sessions/page")
    public Result<PageResult<SessionVO>> page(HttpServletRequest request, @Valid SessionQueryDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(sessionRecordService.pageQuery(userId, dto));
    }

    /**
     * 更新用户会话（标题/摘要/状态）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      会话 ID
     * @param dto     更新参数
     * @return 更新后的会话视图对象
     */
    @Operation(summary = "更新用户会话")
    @PutMapping("/sessions/{id}")
    public Result<SessionVO> update(HttpServletRequest request, @PathVariable("id") Long id,
                                    @Valid @RequestBody SessionUpdateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(sessionRecordService.update(userId, id, dto));
    }

    /**
     * 删除用户会话（逻辑删除）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      会话 ID
     * @return 操作结果
     */
    @Operation(summary = "删除用户会话")
    @DeleteMapping("/sessions/{id}")
    public Result<Void> delete(HttpServletRequest request, @PathVariable("id") Long id) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        sessionRecordService.delete(userId, id);
        return Result.success();
    }
}
