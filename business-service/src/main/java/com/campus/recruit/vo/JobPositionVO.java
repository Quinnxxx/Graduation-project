package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 校招岗位视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "校招岗位信息")
public class JobPositionVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 岗位 ID */
    @Schema(description = "岗位ID")
    private Long id;

    /** 公司名称 */
    @Schema(description = "公司名称")
    private String companyName;

    /** 岗位名称 */
    @Schema(description = "岗位名称")
    private String positionName;

    /** 行业 */
    @Schema(description = "行业")
    private String industry;

    /** 岗位类别 */
    @Schema(description = "岗位类别")
    private String jobCategory;

    /** 工作地点 */
    @Schema(description = "工作地点")
    private String workCity;

    /** 月薪下限，单位 K */
    @Schema(description = "月薪下限(K)")
    private BigDecimal salaryMin;

    /** 月薪上限，单位 K */
    @Schema(description = "月薪上限(K)")
    private BigDecimal salaryMax;

    /** 薪资原文 */
    @Schema(description = "薪资原文")
    private String salaryNote;

    /** 学历要求：0不限 1本科 2硕士 3博士 */
    @Schema(description = "学历要求：0不限 1本科 2硕士 3博士")
    private Integer educationRequirement;

    /** 学历要求原文 */
    @Schema(description = "学历要求原文")
    private String educationText;

    /** 岗位职责描述 */
    @Schema(description = "岗位职责描述")
    private String jobDescription;

    /** 任职要求 */
    @Schema(description = "任职要求")
    private String jobRequirement;

    /** 来源渠道 */
    @Schema(description = "来源渠道")
    private String sourceChannel;

    /** 原文链接 */
    @Schema(description = "原文链接")
    private String sourceUrl;

    /** 发布时间 */
    @Schema(description = "发布时间")
    private LocalDate publishTime;

    /** 投递截止时间 */
    @Schema(description = "投递截止时间")
    private LocalDateTime deadline;

    /** 状态：1在招 0已下架 */
    @Schema(description = "状态：1在招 0已下架")
    private Integer status;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
