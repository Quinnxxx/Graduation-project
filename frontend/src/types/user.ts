/**
 * 用户相关类型定义
 *
 * 与后端 SysUser / LoginVO / 各 DTO 字段对齐
 */

/** 用户信息（对应后端 SysUserVO） */
export interface UserInfo {
  /** 用户 ID */
  id: number
  /** 用户名 */
  username: string
  /** 昵称 */
  nickname: string
  /** 邮箱 */
  email: string
  /** 手机号 */
  phone?: string
  /** 头像 URL */
  avatar?: string
  /** 账号状态：1 启用，0 禁用 */
  status: number
  /** 最近登录时间 */
  lastLoginTime?: string
  /** 创建时间 */
  createTime?: string
}

/** 登录参数（对应后端 LoginDTO） */
export interface LoginParams {
  /** 用户名 */
  username: string
  /** 密码 */
  password: string
}

/** 注册参数（对应后端 RegisterDTO） */
export interface RegisterParams {
  /** 用户名（4-32 位，字母数字下划线） */
  username: string
  /** 密码（6-32 位） */
  password: string
  /** 确认密码，需与 password 一致 */
  confirmPassword: string
  /** 昵称 */
  nickname: string
  /** 邮箱 */
  email: string
  /** 手机号（可选） */
  phone?: string
}

/** 登录结果（对应后端 LoginVO） */
export interface LoginResult {
  /** JWT 访问令牌 */
  token: string
  /** 令牌类型，固定 Bearer */
  tokenType: string
  /** 令牌有效期（秒） */
  expiresIn: number
  /** 用户信息 */
  user: UserInfo
}

/** 更新用户参数（对应后端 UserUpdateDTO） */
export interface UpdateUserParams {
  /** 昵称 */
  nickname: string
  /** 邮箱 */
  email: string
  /** 手机号（可选） */
  phone?: string
  /** 头像 URL（可选） */
  avatar?: string
  /** 账号状态：1 启用，0 禁用 */
  status: number
}
