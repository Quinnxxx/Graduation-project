package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 更新简历记录请求参数（AI 优化回填）
 *
 * <p>字段级更新约定：null 表示不修改该字段；仅对显式传值的字段生效。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "更新简历记录请求参数")
public class ResumeUpdateDTO {

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
