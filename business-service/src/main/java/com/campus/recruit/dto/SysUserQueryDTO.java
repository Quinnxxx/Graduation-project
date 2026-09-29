package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 用户分页查询参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户分页查询参数")
public class SysUserQueryDTO {

    /** 页码 */
    @Schema(description = "页码", example = "1")
    @NotNull(message = "页码不能为空")
    @Min(value = 1, message = "页码最小为1")
    private Integer pageNum = 1;

    /** 每页条数 */
    @Schema(description = "每页条数", example = "10")
    @NotNull(message = "每页条数不能为空")
    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数最大为100")
    private Integer pageSize = 10;

    /** 用户名（模糊查询，可选） */
    @Schema(description = "用户名（模糊查询，可选）")
    private String username;

    /** 账号状态（可选） */
    @Schema(description = "账号状态（可选）：1启用，0禁用")
    private Integer status;
}
