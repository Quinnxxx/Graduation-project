package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 模拟面试分页查询请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "模拟面试分页查询请求参数")
public class InterviewQueryDTO {

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

    /** 面试类型：1技术面 2HR面 */
    @Schema(description = "面试类型：1技术面 2HR面")
    @Min(value = 1, message = "面试类型取值必须在1-2之间")
    @Max(value = 2, message = "面试类型取值必须在1-2之间")
    private Integer interviewType;
}
