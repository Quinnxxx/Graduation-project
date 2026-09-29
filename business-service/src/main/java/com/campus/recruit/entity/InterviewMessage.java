package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 面试消息实体
 *
 * <p>对应表 interview_message，记录面试过程的逐条对话（普通表，无逻辑删除与更新时间），
 * 支撑复盘报告生成和长期记忆沉淀。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@TableName("interview_message")
public class InterviewMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（雪花算法生成） */
    @TableId(value = "id", type = IdType.ASSIGN_ID)
    private Long id;

    /** 所属面试记录 ID */
    private Long interviewRecordId;

    /** 消息角色：user/assistant */
    private String role;

    /** 消息类型：question问题/answer回答/evaluation点评 */
    private String messageType;

    /** 消息内容 */
    private String content;

    /** 本条点评评分 0-100（可空） */
    private Integer score;

    /** 创建时间（插入时自动填充，数据库 DEFAULT CURRENT_TIMESTAMP 兜底） */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
