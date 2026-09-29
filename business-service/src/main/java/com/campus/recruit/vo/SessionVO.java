package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户会话视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户会话信息")
public class SessionVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 会话 ID */
    @Schema(description = "会话ID")
    private Long id;

    /** 用户 ID */
    @Schema(description = "用户ID")
    private Long userId;

    /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
    @Schema(description = "会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答")
    private Integer sessionType;

    /** 处理的 Agent 名称 */
    @Schema(description = "处理的Agent名称")
    private String agentName;

    /** 会话标题 */
    @Schema(description = "会话标题")
    private String title;

    /** 会话摘要 */
    @Schema(description = "会话摘要")
    private String summary;

    /** 状态：1进行中 2已完成 */
    @Schema(description = "状态：1进行中 2已完成")
    private Integer status;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    /** 更新时间 */
    @Schema(description = "更新时间")
    private LocalDateTime updateTime;
}
