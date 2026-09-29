package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 模拟面试视图对象
 *
 * <p>messages 仅在详情接口组装，分页列表接口为 null 或空。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "模拟面试信息")
public class InterviewVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 面试记录 ID */
    @Schema(description = "面试记录ID")
    private Long id;

    /** 用户 ID */
    @Schema(description = "用户ID")
    private Long userId;

    /** 面试类型：1技术面 2HR面 */
    @Schema(description = "面试类型：1技术面 2HR面")
    private Integer interviewType;

    /** 目标公司 */
    @Schema(description = "目标公司")
    private String targetCompany;

    /** 目标岗位 */
    @Schema(description = "目标岗位")
    private String targetPosition;

    /** 难度：1简单 2中等 3困难 */
    @Schema(description = "难度：1简单 2中等 3困难")
    private Integer difficultyLevel;

    /** 关联简历记录 ID（resume_record.id，可为空） */
    @Schema(description = "关联简历记录ID（可选）")
    private Long resumeId;

    /** 面试时长（秒） */
    @Schema(description = "面试时长（秒）")
    private Integer durationSeconds;

    /** 提问数量 */
    @Schema(description = "提问数量")
    private Integer questionCount;

    /** 综合评分 0-100 */
    @Schema(description = "综合评分0-100")
    private Integer overallScore;

    /** 面试复盘报告 */
    @Schema(description = "面试复盘报告")
    private String evaluationReport;

    /** 状态：1进行中 2已完成 3已中断 */
    @Schema(description = "状态：1进行中 2已完成 3已中断")
    private Integer status;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    /** 更新时间 */
    @Schema(description = "更新时间")
    private LocalDateTime updateTime;

    /** 面试对话消息列表（详情接口组装） */
    @Schema(description = "面试对话消息列表（详情接口组装）")
    private List<InterviewMessageVO> messages;
}
