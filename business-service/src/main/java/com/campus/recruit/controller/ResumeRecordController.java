package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.dto.ResumeQueryDTO;
import com.campus.recruit.dto.ResumeSaveDTO;
import com.campus.recruit.dto.ResumeUpdateDTO;
import com.campus.recruit.service.ResumeRecordService;
import com.campus.recruit.vo.ResumeUploadVO;
import com.campus.recruit.vo.ResumeVO;
import com.campus.recruit.config.JwtAuthInterceptor;
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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 简历记录接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "简历记录", description = "简历优化记录管理与查询")
@RestController
@RequiredArgsConstructor
@Validated
public class ResumeRecordController {

    private final ResumeRecordService resumeRecordService;

    /**
     * 创建简历记录
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     创建参数
     * @return 简历记录视图对象
     */
    @Operation(summary = "创建简历记录")
    @PostMapping("/resumes")
    public Result<ResumeVO> create(HttpServletRequest request, @Valid @RequestBody ResumeSaveDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(resumeRecordService.create(userId, dto));
    }

    /**
     * 上传 PDF 简历（校验、落盘并提取文本，不落库）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param file    PDF 文件（multipart/form-data，≤5MB）
     * @return 上传结果（fileName / fileSize / filePath / text）
     */
    @Operation(summary = "上传 PDF 简历并提取文本")
    @PostMapping("/resumes/upload")
    public Result<ResumeUploadVO> upload(HttpServletRequest request,
                                         @RequestParam("file") MultipartFile file) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(resumeRecordService.uploadPdf(userId, file));
    }

    /**
     * 分页查询我的简历记录
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     分页参数（GET 查询参数）
     * @return 分页结果
     */
    @Operation(summary = "分页查询我的简历记录")
    @GetMapping("/resumes/page")
    public Result<PageResult<ResumeVO>> page(HttpServletRequest request, @Valid ResumeQueryDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(resumeRecordService.pageQuery(userId, dto));
    }

    /**
     * 查询简历记录详情
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      记录 ID
     * @return 简历记录视图对象
     */
    @Operation(summary = "查询简历记录详情")
    @GetMapping("/resumes/{id}")
    public Result<ResumeVO> detail(HttpServletRequest request, @PathVariable("id") Long id) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(resumeRecordService.getDetail(userId, id));
    }

    /**
     * 更新简历记录（AI 优化回填）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      记录 ID
     * @param dto     更新参数
     * @return 更新后的简历记录视图对象
     */
    @Operation(summary = "更新简历记录（AI优化回填）")
    @PutMapping("/resumes/{id}")
    public Result<ResumeVO> update(HttpServletRequest request, @PathVariable("id") Long id,
                                   @Valid @RequestBody ResumeUpdateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(resumeRecordService.update(userId, id, dto));
    }

    /**
     * 删除简历记录（逻辑删除）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param id      记录 ID
     * @return 操作结果
     */
    @Operation(summary = "删除简历记录")
    @DeleteMapping("/resumes/{id}")
    public Result<Void> delete(HttpServletRequest request, @PathVariable("id") Long id) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        resumeRecordService.delete(userId, id);
        return Result.success();
    }
}
