package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;

/**
 * 内部批量岗位条目
 *
 * <p>采集 Agent 推送的单个岗位记录。字段为采集侧提交面（snake_case 由容器层
 * 保持），写入实体时的映射见 {@code InternalJobServiceImpl}；job_category 为
 * 岗位类别，写入 {@code job_position.job_category}；ext_company 为采集侧附加
 * 信息，当前表结构无对应列，暂不落库。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "内部批量岗位条目")
public class InternalJobItemDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 岗位名称 */
    @Schema(description = "岗位名称", example = "Java 后端开发工程师")
    @NotBlank(message = "岗位名称不能为空")
    private String jobTitle;

    /** 岗位类别（可选），落 job_category 列，如 后端开发/前端开发/AI算法 */
    @Schema(description = "岗位类别（可选）", example = "后端开发")
    @Size(max = 32, message = "岗位类别长度不能超过32")
    private String jobCategory;

    /** 公司名称 */
    @Schema(description = "公司名称", example = "某某科技")
    @NotBlank(message = "公司名称不能为空")
    private String companyName;

    /** 工作城市（可选） */
    @Schema(description = "工作城市（可选）", example = "北京")
    private String city;

    /** 薪资原文（可选），如 15K-25K·14薪 */
    @Schema(description = "薪资原文（可选）", example = "15K-25K·14薪")
    private String salaryRange;

    /** 岗位正文 / 职责描述（可选） */
    @Schema(description = "岗位正文/职责描述（可选）")
    private String jobDetails;

    /** 发布时间（可选） */
    @Schema(description = "发布时间（可选）", example = "2026-09-01")
    private LocalDate publishDate;

    /** 采集源原文链接（可选，不超过 500 字符） */
    @Schema(description = "采集源原文链接（可选）", example = "https://example.com/jobs/1")
    @Size(max = 500, message = "原文链接长度不能超过500")
    private String link;

    /** 外部公司标识（可选，当前无对应列，暂不落库） */
    @Schema(description = "外部公司标识（可选）")
    private String extCompany;

    /** 数据来源渠道（可选），落 job_position.source_channel 列，如 jobsys / sample_jobs */
    @Schema(description = "数据来源渠道（可选）", example = "jobsys")
    @Size(max = 32, message = "来源渠道长度不能超过32")
    private String sourceChannel;
}