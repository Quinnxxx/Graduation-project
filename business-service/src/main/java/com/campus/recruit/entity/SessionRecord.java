package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 用户会话记录实体
 *
 * <p>对应表 session_record，记录用户每次任务会话，供历史记录页和个人中心展示。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("session_record")
public class SessionRecord extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    private Long userId;

    /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
    private Integer sessionType;

    /** 处理的 Agent 名称 */
    private String agentName;

    /** 会话标题 */
    private String title;

    /** 会话摘要 */
    private String summary;

    /** 状态：1进行中 2已完成 */
    private Integer status;
}
