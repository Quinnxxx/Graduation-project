package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

/**
 * 登录成功返回体
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "登录成功返回体")
public class LoginVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 访问令牌 */
    @Schema(description = "JWT访问令牌")
    private String token;

    /** 令牌类型 */
    @Schema(description = "令牌类型", example = "Bearer")
    private String tokenType;

    /** 令牌有效期（秒） */
    @Schema(description = "令牌有效期（秒）")
    private Long expiresIn;

    /** 用户信息 */
    @Schema(description = "用户信息")
    private SysUserVO user;
}
