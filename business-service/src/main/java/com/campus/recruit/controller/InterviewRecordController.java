package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.InterviewCreateDTO;
import com.campus.recruit.dto.InterviewMessageDTO;
import com.campus.recruit.dto.InterviewQueryDTO;
import com.campus.recruit.dto.InterviewUpdateDTO;
import com.campus.recruit.service.InterviewRecordService;
import com.campus.recruit.vo.InterviewMessageVO;
import com.campus.recruit.vo.InterviewVO;
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
 * 模拟面试接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "模拟面试", description = "模拟面试记录管理与对话消息")
@RestController
@RequiredArgsConstructor
@Validated
public class InterviewRecordController {

    private final InterviewRecordService interviewRecordService;

    /**
     * 创建模拟面试
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     创建参数
     * @return 面试视图对象
     */
    @Operation(summary = "创建模拟面试")
    @PostMapping("/interviews")
    public Result<InterviewVO> create(HttpServletRequest request, @Valid @RequestBody InterviewCreateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(interviewRecordService.create(userId, dto));
    }

    /**
     * 分页查询我的面试记录
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     分页参数（GET 查询参数）
     * @return 分页结果
     */
    @Operation(summary = "分页查询我的面试记录")
    @GetMapping("/interviews/page")
    public Result<PageResult<InterviewVO>> page(HttpServletRequest request, @Valid InterviewQueryDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(interviewRecordService.pageQuery(userId, dto));
    }

    /**
     * 查询面试详情（含对话消息）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      面试记录 ID
     * @return 面试视图对象
     */
    @Operation(summary = "查询面试详情(含对话消息)")
    @GetMapping("/interviews/{id}")
    public Result<InterviewVO> detail(HttpServletRequest request, @PathVariable("id") Long id) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(interviewRecordService.getDetail(userId, id));
    }

    /**
     * 更新面试记录（结束回填）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      面试记录 ID
     * @param dto     更新参数
     * @return 更新后的面试视图对象
     */
    @Operation(summary = "更新面试记录(结束回填)")
    @PutMapping("/interviews/{id}")
    public Result<InterviewVO> update(HttpServletRequest request, @PathVariable("id") Long id,
                                      @Valid @RequestBody InterviewUpdateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(interviewRecordService.update(userId, id, dto));
    }

    /**
     * 追加面试消息
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      面试记录 ID
     * @param dto     消息参数
     * @return 消息视图对象
     */
    @Operation(summary = "追加面试消息")
    @PostMapping("/interviews/{id}/messages")
    public Result<InterviewMessageVO> addMessage(HttpServletRequest request, @PathVariable("id") Long id,
                                                 @Valid @RequestBody InterviewMessageDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(interviewRecordService.addMessage(userId, id, dto));
    }

    /**
     * 删除面试记录（逻辑删除记录并物理删除消息）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      面试记录 ID
     * @return 操作结果
     */
    @Operation(summary = "删除面试记录")
    @DeleteMapping("/interviews/{id}")
    public Result<Void> delete(HttpServletRequest request, @PathVariable("id") Long id) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        interviewRecordService.delete(userId, id);
        return Result.success();
    }
}
