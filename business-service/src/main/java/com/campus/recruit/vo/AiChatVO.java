package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * AI 对话非流式响应视图对象
 *
 * <p>对外字段沿用项目统一的 camelCase 命名；AI 服务返回的 snake_case data
 * 由转发层专用的 SNAKE_CASE ObjectMapper 映射成本对象。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "AI 对话非流式响应视图对象")
public class AiChatVO {

    /** 实际处理该请求的 Agent 名称（job/resume/tech/hr/chat） */
    @Schema(description = "处理 Agent 名称")
    private String agentName;

    /** 完整回复内容（Markdown） */
    @Schema(description = "完整回复内容")
    private String finalResponse;

    /** 错误信息，正常时为 null */
    @Schema(description = "错误信息，正常时为 null")
    private String error;
}
