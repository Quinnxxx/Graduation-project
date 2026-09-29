package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 登录请求参数
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "登录请求参数")
public class LoginDTO {

    /** 用户名 */
    @Schema(description = "用户名", example = "campus_user")
    @NotBlank(message = "用户名不能为空")
    @Size(min = 4, max = 32, message = "用户名长度必须在4-32之间")
    private String username;

    /** 密码 */
    @Schema(description = "密码", example = "123456")
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 32, message = "密码长度必须在6-32之间")
    private String password;
}
