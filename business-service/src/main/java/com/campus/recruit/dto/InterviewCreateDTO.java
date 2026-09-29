package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 创建模拟面试请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "创建模拟面试请求参数")
public class InterviewCreateDTO {

    /** 面试类型：1技术面 2HR面 */
    @Schema(description = "面试类型：1技术面 2HR面", example = "1")
    @NotNull(message = "面试类型不能为空")
    @Min(value = 1, message = "面试类型取值必须在1-2之间")
    @Max(value = 2, message = "面试类型取值必须在1-2之间")
    private Integer interviewType;

    /** 目标公司 */
    @Schema(description = "目标公司")
    private String targetCompany;

    /** 目标岗位 */
    @Schema(description = "目标岗位")
    private String targetPosition;

    /** 难度：1简单 2中等 3困难，默认2 */
    @Schema(description = "难度：1简单 2中等 3困难，默认2", example = "2")
    @Min(value = 1, message = "难度取值必须在1-3之间")
    @Max(value = 3, message = "难度取值必须在1-3之间")
    private Integer difficultyLevel;

    /** 关联简历记录 ID（resume_record.id，可为空，为空时由 AI 按通用题库提问） */
    @Schema(description = "关联简历记录ID（可选）")
    private Long resumeId;
}
