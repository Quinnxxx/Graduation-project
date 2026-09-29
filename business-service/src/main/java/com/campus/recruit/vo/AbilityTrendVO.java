package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;

/**
 * 能力成长曲线数据点视图对象
 *
 * <p>趋势查询返回的数据点，不含 id/userId，仅用于绘制成长曲线。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "能力成长曲线数据点")
public class AbilityTrendVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 能力维度 */
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
}
