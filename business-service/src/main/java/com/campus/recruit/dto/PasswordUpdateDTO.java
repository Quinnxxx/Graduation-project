package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * 修改密码请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "修改密码请求参数")
public class PasswordUpdateDTO {

    /** 旧密码 */
    @Schema(description = "旧密码", example = "123456")
    @NotBlank(message = "旧密码不能为空")
    private String oldPassword;

    /** 新密码 */
    @Schema(description = "新密码", example = "abc12345")
    @NotBlank(message = "新密码不能为空")
    @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d).{8,32}$", message = "新密码长度需8-32位且包含字母和数字")
    private String newPassword;

    /** 确认密码 */
    @Schema(description = "确认密码", example = "abc12345")
    @NotBlank(message = "确认密码不能为空")
    private String confirmPassword;
}
