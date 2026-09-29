package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 * 校招岗位统计视图对象
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "校招岗位统计")
public class JobStatsVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 在招岗位总数 */
    @Schema(description = "在招岗位总数")
    private Long totalCount;

    /** 按岗位类别分组计数 */
    @Schema(description = "按岗位类别分组计数")
    private List<NameCountVO> categoryCounts;

    /** 按城市分组计数(Top10) */
    @Schema(description = "按城市分组计数(Top10)")
    private List<NameCountVO> cityCounts;

    /**
     * 名称-数量统计项
     *
     * @author campus-recruit
     * @since 1.0.0
     */
    @Data
    @Schema(description = "名称-数量统计项")
    public static class NameCountVO implements Serializable {

        private static final long serialVersionUID = 1L;

        /** 分组名称（类别或城市） */
        @Schema(description = "分组名称（类别或城市）")
        private String name;

        /** 数量 */
        @Schema(description = "数量")
        private Long count;
    }
}
