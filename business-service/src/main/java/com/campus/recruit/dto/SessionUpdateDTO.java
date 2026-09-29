package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 更新用户会话请求参数
 *
 * <p>字段级更新约定：null 表示不修改该字段；仅对显式传值的字段生效。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "更新用户会话请求参数")
public class SessionUpdateDTO {

    /** 会话标题 */
    @Schema(description = "会话标题")
    private String title;

    /** 会话摘要 */
    @Schema(description = "会话摘要")
    private String summary;

    /** 状态：1进行中 2已完成 */
    @Schema(description = "状态：1进行中 2已完成")
    @Min(value = 1, message = "状态取值必须在1-2之间")
    @Max(value = 2, message = "状态取值必须在1-2之间")
    private Integer status;
}
