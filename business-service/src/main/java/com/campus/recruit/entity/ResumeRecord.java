package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 简历优化记录实体
 *
 * <p>对应表 resume_record，每次简历优化生成一条记录，供历史查询和能力复盘。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("resume_record")
public class ResumeRecord extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    private Long userId;

    /** 简历标题 */
    private String resumeTitle;

    /** 原始简历文本 */
    private String originalContent;

    /** 优化后简历文本 */
    private String optimizedContent;

    /** 目标岗位名称 */
    private String targetPositionName;

    /** 优化建议 JSON 字符串 */
    private String optimizationSuggestions;

    /** 优化前评分 0-100 */
    private Integer resumeScore;

    /** 优化后评分 0-100 */
    private Integer optimizedScore;

    /** 状态：1已完成 0处理中 */
    private Integer status;

    /** 上传简历原始文件名 */
    private String fileName;

    /** 简历文件存储相对路径 */
    private String filePath;

    /** 简历文件字节数 */
    private Long fileSize;
}
