/**
 * 本地存储工具
 *
 * 统一管理 token 等持久化信息的存取，避免散落 localStorage 调用。
 */

/** token 存储键名 */
const TOKEN_KEY = 'campus_recruit_token'

/** 用户信息存储键名 */
const USER_INFO_KEY = 'campus_recruit_user_info'

/**
 * 获取本地存储的 token
 *
 * @returns token 字符串，不存在时返回空字符串
 */
export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 保存 token 到本地存储
 *
 * @param token JWT 令牌
 */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 移除本地存储的 token
 */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 获取本地存储的用户信息
 *
 * @returns 用户信息对象，不存在时返回 null
 */
export function getUserInfo<T = unknown>(): T | null {
  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/**
 * 保存用户信息到本地存储
 *
 * @param info 用户信息对象
 */
export function setUserInfo(info: unknown): void {
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(info))
}

/**
 * 移除本地存储的用户信息
 */
export function removeUserInfo(): void {
  localStorage.removeItem(USER_INFO_KEY)
}
