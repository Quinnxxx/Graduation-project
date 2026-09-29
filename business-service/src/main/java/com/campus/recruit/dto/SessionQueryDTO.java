package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 用户会话分页查询请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户会话分页查询请求参数")
public class SessionQueryDTO {

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

    /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
    @Schema(description = "会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答")
    @Min(value = 1, message = "会话类型取值必须在1-5之间")
    @Max(value = 5, message = "会话类型取值必须在1-5之间")
    private Integer sessionType;
}
