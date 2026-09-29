package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 简历记录视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "简历记录信息")
public class ResumeVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 记录 ID */
    @Schema(description = "记录ID")
    private Long id;

    /** 用户 ID */
    @Schema(description = "用户ID")
    private Long userId;

    /** 简历标题 */
    @Schema(description = "简历标题")
    private String resumeTitle;

    /** 原始简历文本 */
    @Schema(description = "原始简历文本")
    private String originalContent;

    /** 优化后简历文本 */
    @Schema(description = "优化后简历文本")
    private String optimizedContent;

    /** 目标岗位名称 */
    @Schema(description = "目标岗位名称")
    private String targetPositionName;

    /** 优化建议 JSON 字符串 */
    @Schema(description = "优化建议JSON字符串")
    private String optimizationSuggestions;

    /** 优化前评分 0-100 */
    @Schema(description = "优化前评分0-100")
    private Integer resumeScore;

    /** 优化后评分 0-100 */
    @Schema(description = "优化后评分0-100")
    private Integer optimizedScore;

    /** 状态：1已完成 0处理中 */
    @Schema(description = "状态：1已完成 0处理中")
    private Integer status;

    /** 上传简历原始文件名 */
    @Schema(description = "上传简历原始文件名")
    private String fileName;

    /** 简历文件字节数 */
    @Schema(description = "简历文件字节数")
    private Long fileSize;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    /** 更新时间 */
    @Schema(description = "更新时间")
    private LocalDateTime updateTime;
}
