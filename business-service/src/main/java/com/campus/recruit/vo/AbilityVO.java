package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 能力画像快照视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "能力画像快照信息")
public class AbilityVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 快照 ID */
    @Schema(description = "快照ID")
    private Long id;

    /** 用户 ID */
    @Schema(description = "用户ID")
    private Long userId;

    /** 能力维度：如 技术基础/项目经验/沟通表达/逻辑思维/岗位匹配度 */
    @Schema(description = "能力维度")
    private String dimension;

    /** 维度得分 0-100 */
    @Schema(description = "维度得分0-100")
    private Integer dimensionScore;

    /** 维度评语 */
    @Schema(description = "维度评语")
    private String evaluation;

    /** 快照日期 */
    @Schema(description = "快照日期")
    private LocalDate snapshotDate;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
