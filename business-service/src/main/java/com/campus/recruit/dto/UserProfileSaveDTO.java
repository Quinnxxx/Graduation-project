package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

import java.util.List;

/**
 * 用户求职画像保存请求参数
 *
 * <p>全部字段可选，由前端引导填写；skillTags 前端传字符串列表，后端统一转 JSON 字符串存储。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户求职画像保存请求参数")
public class UserProfileSaveDTO {

    /** 目标岗位 */
    @Schema(description = "目标岗位", example = "后端开发工程师")
    private String targetPosition;

    /** 目标行业 */
    @Schema(description = "目标行业", example = "互联网")
    private String targetIndustry;

    /** 意向城市 */
    @Schema(description = "意向城市", example = "北京,上海")
    private String cityPreference;

    /** 学历：0其他 1本科 2硕士 3博士 */
    @Schema(description = "学历：0其他 1本科 2硕士 3博士", example = "1")
    @Min(value = 0, message = "学历取值必须在0-3之间")
    @Max(value = 3, message = "学历取值必须在0-3之间")
    private Integer education;

    /** 学校名称 */
    @Schema(description = "学校名称", example = "某某大学")
    private String school;

    /** 专业名称 */
    @Schema(description = "专业名称", example = "计算机科学与技术")
    private String major;

    /** 毕业年份 */
    @Schema(description = "毕业年份", example = "2027")
    @Min(value = 2000, message = "毕业年份不能早于2000年")
    @Max(value = 2100, message = "毕业年份不能晚于2100年")
    private Integer graduationYear;

    /** 技能标签列表（允许为空） */
    @Schema(description = "技能标签列表", example = "[\"Java\",\"Spring\"]")
    private List<String> skillTags;

    /** 求职意向描述 */
    @Schema(description = "求职意向描述", example = "期望从事后端开发，倾向大厂")
    private String careerIntention;

    /** 自我评价 */
    @Schema(description = "自我评价", example = "三年Java开发经验，熟悉微服务架构")
    private String selfEvaluation;
}
