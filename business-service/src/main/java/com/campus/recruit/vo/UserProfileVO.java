package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

/**
 * 用户求职画像视图对象
 *
 * <p>skillTags 以 {@link List} 形式返回，由后端从 JSON 字符串转换。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户求职画像视图对象")
public class UserProfileVO {

    /** 用户ID */
    @Schema(description = "用户ID")
    private Long userId;

    /** 目标岗位 */
    @Schema(description = "目标岗位")
    private String targetPosition;

    /** 目标行业 */
    @Schema(description = "目标行业")
    private String targetIndustry;

    /** 意向城市 */
    @Schema(description = "意向城市")
    private String cityPreference;

    /** 学历：0其他 1本科 2硕士 3博士 */
    @Schema(description = "学历：0其他 1本科 2硕士 3博士")
    private Integer education;

    /** 学校名称 */
    @Schema(description = "学校名称")
    private String school;

    /** 专业名称 */
    @Schema(description = "专业名称")
    private String major;

    /** 毕业年份 */
    @Schema(description = "毕业年份")
    private Integer graduationYear;

    /** 技能标签列表 */
    @Schema(description = "技能标签列表")
    private List<String> skillTags;

    /** 求职意向描述 */
    @Schema(description = "求职意向描述")
    private String careerIntention;

    /** 自我评价 */
    @Schema(description = "自我评价")
    private String selfEvaluation;

    /** 状态：1启用 0停用 */
    @Schema(description = "状态：1启用 0停用")
    private Integer status;
}
