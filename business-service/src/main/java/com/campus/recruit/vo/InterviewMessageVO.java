package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 面试消息视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "面试消息信息")
public class InterviewMessageVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 消息 ID */
    @Schema(description = "消息ID")
    private Long id;

    /** 所属面试记录 ID */
    @Schema(description = "所属面试记录ID")
    private Long interviewRecordId;

    /** 消息角色：user/assistant */
    @Schema(description = "消息角色：user/assistant")
    private String role;

    /** 消息类型：question问题/answer回答/evaluation点评 */
    @Schema(description = "消息类型：question问题/answer回答/evaluation点评")
    private String messageType;

    /** 消息内容 */
    @Schema(description = "消息内容")
    private String content;

    /** 本条点评评分 0-100（可空） */
    @Schema(description = "本条点评评分0-100（可空）")
    private Integer score;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
