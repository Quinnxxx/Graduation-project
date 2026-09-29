package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 注册请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "注册请求参数")
public class RegisterDTO {

    /** 用户名 */
    @Schema(description = "用户名", example = "campus_user")
    @NotBlank(message = "用户名不能为空")
    @Size(min = 4, max = 32, message = "用户名长度必须在4-32之间")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "用户名只能包含字母、数字和下划线")
    private String username;

    /** 密码 */
    @Schema(description = "密码", example = "123456")
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 32, message = "密码长度必须在6-32之间")
    @Pattern(regexp = "^[a-zA-Z0-9_@#$.]+$", message = "密码包含非法字符")
    private String password;

    /** 确认密码 */
    @Schema(description = "确认密码", example = "123456")
    @NotBlank(message = "确认密码不能为空")
    private String confirmPassword;

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
}
