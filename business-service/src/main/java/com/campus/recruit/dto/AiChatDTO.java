package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * AI 对话转发请求参数
 *
 * <p>由前端提交，用户身份（user_id）不在此传入，统一由转发层从当前登录用户
 * JWT 解析后注入，避免越权伪造。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "AI 对话转发请求参数")
public class AiChatDTO {

    /** 业务侧会话标识（可空，AI 服务当前不落库，预留） */
    @Schema(description = "会话标识（可空）")
    private String sessionId;

    /** 用户输入内容 */
    @Schema(description = "用户输入内容", example = "帮我推荐广州的后端开发岗位")
    @NotBlank(message = "对话内容不能为空")
    private String query;

    /** 前端透传的简历文本（简历优化 / 面试场景使用，可空） */
    @Schema(description = "简历文本（可空）")
    private String resumeText;
}
