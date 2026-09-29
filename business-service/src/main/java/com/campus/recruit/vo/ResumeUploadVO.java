package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

/**
 * 简历 PDF 上传结果视图对象
 *
 * <p>由 {@code POST /resumes/upload} 返回，前端填充表单后再走既有
 * {@code POST /resumes} 创建；本对象不落库。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "简历 PDF 上传结果")
public class ResumeUploadVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 上传简历原始文件名 */
    @Schema(description = "上传简历原始文件名")
    private String fileName;

    /** 简历文件字节数 */
    @Schema(description = "简历文件字节数")
    private Long fileSize;

    /** 简历文件存储相对路径（随创建请求回传，落库用） */
    @Schema(description = "简历文件存储相对路径")
    private String filePath;

    /** PDF 提取出的简历文本 */
    @Schema(description = "PDF 提取出的简历文本")
    private String text;
}
