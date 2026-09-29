package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 创建简历记录请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "创建简历记录请求参数")
public class ResumeSaveDTO {

    /** 简历标题 */
    @Schema(description = "简历标题")
    @NotBlank(message = "简历标题不能为空")
    private String resumeTitle;

    /** 原始简历文本 */
    @Schema(description = "原始简历文本")
    @NotBlank(message = "简历内容不能为空")
    private String originalContent;

    /** 目标岗位名称 */
    @Schema(description = "目标岗位名称")
    private String targetPositionName;

    /** 上传简历原始文件名（可空，PDF 上传路径） */
    @Schema(description = "上传简历原始文件名（可空）")
    private String fileName;

    /** 简历文件存储相对路径（可空，由上传接口返回） */
    @Schema(description = "简历文件存储相对路径（可空）")
    private String filePath;

    /** 简历文件字节数（可空） */
    @Schema(description = "简历文件字节数（可空）")
    private Long fileSize;
}
