package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 更新用户请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "更新用户请求参数")
public class UserUpdateDTO {

    /** 昵称 */
    @Schema(description = "昵称", example = "小明")
    @NotBlank(message = "昵称不能为空")
    @Size(max = 32, message = "昵称长度不能超过32")
    private String nickname;

    /** 邮箱 */
    @Schema(description = "邮箱", example = "user@example.com")
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    /** 手机号 */
    @Schema(description = "手机号", example = "13800138000")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    /** 头像 URL */
    @Schema(description = "头像URL")
    @Size(max = 512, message = "头像地址长度不能超过512")
    private String avatar;

    /** 账号状态：1 启用，0 禁用 */
    @Schema(description = "账号状态：1启用，0禁用")
    @NotNull(message = "账号状态不能为空")
    @Min(value = 0, message = "账号状态只能为0或1")
    @Max(value = 1, message = "账号状态只能为0或1")
    private Integer status;
}
