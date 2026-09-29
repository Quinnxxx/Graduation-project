package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * 系统用户实体
 *
 * <p>对应表 sys_user，存储平台用户账号信息。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("sys_user")
public class SysUser extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /** 登录账号（唯一） */
    private String username;

    /** 登录密码（BCrypt 加密存储，序列化时隐藏） */
    @JsonIgnore
    private String password;

    /** 昵称 */
    private String nickname;

    /** 邮箱 */
    private String email;

    /** 手机号 */
    private String phone;

    /** 头像 URL */
    private String avatar;

    /** 账号状态：1 启用，0 禁用 */
    private Integer status;

    /** 最近登录时间 */
    private LocalDateTime lastLoginTime;
}
