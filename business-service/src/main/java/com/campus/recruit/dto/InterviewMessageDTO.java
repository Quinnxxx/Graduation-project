package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 追加面试消息请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "追加面试消息请求参数")
public class InterviewMessageDTO {

    /** 消息角色：user/assistant */
    @Schema(description = "消息角色：user/assistant", example = "user")
    @NotBlank(message = "消息角色不能为空")
    private String role;

    /** 消息类型：question问题/answer回答/evaluation点评 */
    @Schema(description = "消息类型：question问题/answer回答/evaluation点评", example = "question")
    @NotBlank(message = "消息类型不能为空")
    private String messageType;

    /** 消息内容 */
    @Schema(description = "消息内容")
    @NotBlank(message = "消息内容不能为空")
    private String content;

    /** 本条点评评分 0-100（可空） */
    @Schema(description = "本条点评评分0-100（可空）")
    @Min(value = 0, message = "评分取值必须在0-100之间")
    @Max(value = 100, message = "评分取值必须在0-100之间")
    private Integer score;
}
