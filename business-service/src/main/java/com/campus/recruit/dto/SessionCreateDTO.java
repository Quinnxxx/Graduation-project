package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 创建用户会话请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "创建用户会话请求参数")
public class SessionCreateDTO {

    /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
    @Schema(description = "会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答", example = "1")
    @NotNull(message = "会话类型不能为空")
    @Min(value = 1, message = "会话类型取值必须在1-5之间")
    @Max(value = 5, message = "会话类型取值必须在1-5之间")
    private Integer sessionType;

    /** 处理的 Agent 名称 */
    @Schema(description = "处理的Agent名称")
    private String agentName;

    /** 会话标题（为空默认"新建会话"） */
    @Schema(description = "会话标题，为空默认新建会话")
    private String title;

    /** 会话摘要 */
    @Schema(description = "会话摘要")
    private String summary;
}
