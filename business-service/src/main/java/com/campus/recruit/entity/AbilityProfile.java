package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;

/**
 * 能力画像快照实体
 *
 * <p>对应表 ability_profile，每次面试复盘生成一组各维度快照，
 * 可绘制能力成长曲线，是长期记忆的核心载体。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("ability_profile")
public class AbilityProfile extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    private Long userId;

    /** 能力维度：如 技术基础/项目经验/沟通表达/逻辑思维/岗位匹配度 */
    private String dimension;

    /** 维度得分 0-100 */
    private Integer dimensionScore;

    /** 维度评语 */
    private String evaluation;

    /** 快照日期 */
    private LocalDate snapshotDate;
}
