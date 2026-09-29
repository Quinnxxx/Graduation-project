package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户信息返回体
 *
 * <p>对外输出的用户视图对象，不包含密码等敏感字段。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "用户信息")
public class SysUserVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 用户 ID */
    @Schema(description = "用户ID")
    private Long id;

    /** 用户名 */
    @Schema(description = "用户名")
    private String username;

    /** 昵称 */
    @Schema(description = "昵称")
    private String nickname;

    /** 邮箱 */
    @Schema(description = "邮箱")
    private String email;

    /** 手机号 */
    @Schema(description = "手机号")
    private String phone;

    /** 头像 URL */
    @Schema(description = "头像URL")
    private String avatar;

    /** 账号状态：1 启用，0 禁用 */
    @Schema(description = "账号状态：1启用，0禁用")
    private Integer status;

    /** 最近登录时间 */
    @Schema(description = "最近登录时间")
    private LocalDateTime lastLoginTime;

    /** 创建时间 */
    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
