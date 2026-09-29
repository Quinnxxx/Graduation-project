package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 校招岗位实体
 *
 * <p>对应表 job_position，存储校招岗位数据，由采集 Agent 每日增量写入，本模块只读。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("job_position")
public class JobPosition extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 公司名称 */
    private String companyName;

    /** 岗位名称 */
    private String positionName;

    /** 行业 */
    private String industry;

    /** 岗位类别：如 后端开发/前端开发/AI算法/测试/产品/运营 */
    private String jobCategory;

    /** 工作地点 */
    private String workCity;

    /** 月薪下限，单位 K */
    private BigDecimal salaryMin;

    /** 月薪上限，单位 K */
    private BigDecimal salaryMax;

    /** 薪资原文，如 15-25K·14薪 */
    private String salaryNote;

    /** 学历要求：0不限 1本科 2硕士 3博士 */
    private Integer educationRequirement;

    /** 学历要求原文 */
    private String educationText;

    /** 岗位职责描述 */
    private String jobDescription;

    /** 任职要求 */
    private String jobRequirement;

    /** 来源渠道 */
    private String sourceChannel;

    /** 原文链接 */
    private String sourceUrl;

    /** 去重指纹 MD5(公司+岗位+城市+链接) */
    private String jobHash;

    /** 发布时间 */
    private LocalDate publishTime;

    /** 投递截止时间 */
    private LocalDateTime deadline;

    /** 状态：1在招 0已下架 */
    private Integer status;
}
