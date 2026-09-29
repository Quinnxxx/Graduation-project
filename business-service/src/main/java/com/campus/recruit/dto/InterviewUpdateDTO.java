package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 更新模拟面试请求参数（结束回填）
 *
 * <p>字段级更新约定：null 表示不修改该字段；仅对显式传值的字段生效。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "更新模拟面试请求参数")
public class InterviewUpdateDTO {

    /** 面试时长（秒） */
    @Schema(description = "面试时长（秒）")
    @Min(value = 0, message = "面试时长不能为负数")
    private Integer durationSeconds;

    /** 提问数量 */
    @Schema(description = "提问数量")
    @Min(value = 0, message = "提问数量不能为负数")
    private Integer questionCount;

    /** 综合评分 0-100 */
    @Schema(description = "综合评分0-100")
    @Min(value = 0, message = "综合评分取值必须在0-100之间")
    @Max(value = 100, message = "综合评分取值必须在0-100之间")
    private Integer overallScore;

    /** 面试复盘报告 */
    @Schema(description = "面试复盘报告")
    private String evaluationReport;

    /** 状态：1进行中 2已完成 3已中断 */
    @Schema(description = "状态：1进行中 2已完成 3已中断")
    @Min(value = 1, message = "状态取值必须在1-3之间")
    @Max(value = 3, message = "状态取值必须在1-3之间")
    private Integer status;
}
