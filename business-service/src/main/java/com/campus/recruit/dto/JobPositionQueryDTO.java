package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

/**
 * 校招岗位分页查询请求参数
 *
 * <p>全部筛选条件可选，仅对传入的非空字段生效；status 不传时查询全部状态。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "校招岗位分页查询请求参数")
public class JobPositionQueryDTO {

    /** 当前页码 */
    @Schema(description = "当前页码", example = "1")
    @NotNull(message = "页码不能为空")
    @Min(value = 1, message = "页码最小为1")
    private Integer pageNum = 1;

    /** 每页条数 */
    @Schema(description = "每页条数", example = "10")
    @NotNull(message = "每页条数不能为空")
    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数最大为100")
    private Integer pageSize = 10;

    /** 关键词，模糊匹配岗位名称/公司名称/JD文本 */
    @Schema(description = "关键词，模糊匹配岗位名称/公司名称/JD文本")
    private String keyword;

    /** 公司名称模糊匹配 */
    @Schema(description = "公司名称模糊匹配")
    private String companyName;

    /** 岗位类别精确匹配，如 后端开发/前端开发/AI算法/测试/产品/运营 */
    @Schema(description = "岗位类别精确匹配，如 后端开发/前端开发/AI算法/测试/产品/运营")
    private String jobCategory;

    /** 工作城市精确匹配 */
    @Schema(description = "工作城市精确匹配")
    private String workCity;

    /** 行业精确匹配 */
    @Schema(description = "行业精确匹配")
    private String industry;

    /** 学历要求：0不限 1本科 2硕士 3博士 */
    @Schema(description = "学历要求：0不限 1本科 2硕士 3博士", example = "1")
    @Min(value = 0, message = "学历要求取值必须在0-3之间")
    @Max(value = 3, message = "学历要求取值必须在0-3之间")
    private Integer educationRequirement;

    /** 薪资下限(K)，筛选岗位薪资上限>=该值 */
    @Schema(description = "薪资下限(K)，筛选岗位薪资上限>=该值", example = "15")
    private BigDecimal salaryMin;

    /** 薪资上限(K)，筛选岗位薪资下限<=该值 */
    @Schema(description = "薪资上限(K)，筛选岗位薪资下限<=该值", example = "30")
    private BigDecimal salaryMax;

    /** 状态：1在招 0已下架，不传查全部 */
    @Schema(description = "状态：1在招 0已下架，不传查全部", example = "1")
    private Integer status;
}
