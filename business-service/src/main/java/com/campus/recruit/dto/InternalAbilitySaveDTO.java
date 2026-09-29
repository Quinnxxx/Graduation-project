package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.Data;

import java.time.LocalDate;

/**
 * 内部接口：写入能力画像快照请求参数
 *
 * <p>包含 userId（由 AI 服务从图状态透传）及能力快照字段。</p>
 *
 * @author campus-recruit
 * @since 1.1.0
 */
@Data
@Schema(description = "内部接口：写入能力画像快照请求参数")
public class InternalAbilitySaveDTO {

    /** 用户 ID（由 AI 服务透传） */
    @Schema(description = "用户 ID", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotNull(message = "用户 ID 不能为空")
    @Positive(message = "用户 ID 必须为正整数")
    private Long userId;

    /** 能力维度：如 技术基础/项目经验/沟通表达/逻辑思维/岗位匹配度 */
    @Schema(description = "能力维度", example = "技术基础")
    @NotBlank(message = "能力维度不能为空")
    private String dimension;

    /** 维度得分 0-100 */
    @Schema(description = "维度得分 0-100", example = "85")
    @NotNull(message = "得分不能为空")
    @Min(value = 0, message = "得分 0-100")
    @Max(value = 100, message = "得分 0-100")
    private Integer dimensionScore;

    /** 维度评语 */
    @Schema(description = "维度评语")
    private String evaluation;

    /** 快照日期（为空默认当天） */
    @Schema(description = "快照日期，为空默认当天", example = "2026-09-18")
    private LocalDate snapshotDate;
}
