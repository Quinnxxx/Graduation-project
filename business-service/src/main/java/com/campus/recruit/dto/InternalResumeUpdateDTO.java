package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.Data;

/**
 * 内部接口：更新简历请求参数
 *
 * <p>包含 userId（用于归属校验）及简历更新字段。</p>
 *
 * @author campus-recruit
 * @since 1.1.0
 */
@Data
@Schema(description = "内部接口：更新简历请求参数")
public class InternalResumeUpdateDTO {

    /** 用户 ID（由 AI 服务透传，用于归属校验） */
    @Schema(description = "用户 ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "用户 ID 不能为空")
    @Positive(message = "用户 ID 必须为正整数")
    private Long userId;

    /** 优化后简历文本 */
    @Schema(description = "优化后简历文本")
    private String optimizedContent;

    /** 优化建议 JSON 字符串 */
    @Schema(description = "优化建议 JSON 字符串")
    private String optimizationSuggestions;

    /** 优化前评分 0-100 */
    @Schema(description = "优化前评分 0-100")
    @Min(value = 0, message = "优化前评分取值必须在0-100之间")
    @Max(value = 100, message = "优化前评分取值必须在0-100之间")
    private Integer resumeScore;

    /** 优化后评分 0-100 */
    @Schema(description = "优化后评分 0-100")
    @Min(value = 0, message = "优化后评分取值必须在0-100之间")
    @Max(value = 100, message = "优化后评分取值必须在0-100之间")
    private Integer optimizedScore;

    /** 状态：1已完成 0处理中 */
    @Schema(description = "状态：1已完成 0处理中")
    @Min(value = 0, message = "状态取值必须在0-1之间")
    @Max(value = 1, message = "状态取值必须在0-1之间")
    private Integer status;
}
