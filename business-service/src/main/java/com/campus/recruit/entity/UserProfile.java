package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 用户求职画像实体
 *
 * <p>对应表 user_profile，存储每个用户的求职画像信息，供岗位匹配 Agent 与长期记忆使用。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("user_profile")
public class UserProfile extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 用户ID（关联 sys_user.id，唯一） */
    private Long userId;

    /** 目标岗位 */
    private String targetPosition;

    /** 目标行业 */
    private String targetIndustry;

    /** 意向城市 */
    private String cityPreference;

    /** 学历：0其他 1本科 2硕士 3博士 */
    private Integer education;

    /** 学校名称 */
    private String school;

    /** 专业名称 */
    private String major;

    /** 毕业年份 */
    private Integer graduationYear;

    /** 技能标签（JSON数组字符串，如 ["Java","Spring"]） */
    private String skillTags;

    /** 求职意向描述 */
    private String careerIntention;

    /** 自我评价 */
    private String selfEvaluation;

    /** 状态：1启用 0停用 */
    private Integer status;
}
