package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.Data;

/**
 * 内部接口：创建简历请求参数
 *
 * <p>包含 userId（由 AI 服务从图状态透传，源头为 JWT 解析的真实用户 id）
 * 及简历创建所需字段。</p>
 *
 * @author campus-recruit
 * @since 1.1.0
 */
@Data
@Schema(description = "内部接口：创建简历请求参数")
public class InternalResumeCreateDTO {

    /** 用户 ID（由 AI 服务透传） */
    @Schema(description = "用户 ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "用户 ID 不能为空")
    @Positive(message = "用户 ID 必须为正整数")
    private Long userId;

    /** 简历标题 */
    @Schema(description = "简历标题")
    @NotBlank(message = "简历标题不能为空")
    private String resumeTitle;

    /** 原始简历文本 */
    @Schema(description = "原始简历文本")
    @NotBlank(message = "简历内容不能为空")
    private String originalContent;

    /** 目标岗位名称 */
    @Schema(description = "目标岗位名称")
    private String targetPositionName;
}
