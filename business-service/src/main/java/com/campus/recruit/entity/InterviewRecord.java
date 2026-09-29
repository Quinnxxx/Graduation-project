package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 模拟面试记录实体
 *
 * <p>对应表 interview_record，一次完整面试一条记录，供面试复盘与能力画像沉淀。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("interview_record")
public class InterviewRecord extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    private Long userId;

    /** 面试类型：1技术面 2HR面 */
    private Integer interviewType;

    /** 目标公司 */
    private String targetCompany;

    /** 目标岗位 */
    private String targetPosition;

    /** 难度：1简单 2中等 3困难 */
    private Integer difficultyLevel;

    /** 关联简历记录 ID（resume_record.id，可为空） */
    private Long resumeId;

    /** 面试时长（秒） */
    private Integer durationSeconds;

    /** 提问数量 */
    private Integer questionCount;

    /** 综合评分 0-100 */
    private Integer overallScore;

    /** 面试复盘报告 */
    private String evaluationReport;

    /** 状态：1进行中 2已完成 3已中断 */
    private Integer status;
}
