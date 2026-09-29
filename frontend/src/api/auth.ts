/**
 * 认证与用户接口
 *
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据
 */

import request from './request'

import type { ApiResult } from '@/types/api'
import type { LoginParams, LoginResult, RegisterParams, UserInfo } from '@/types/user'

/**
 * 用户登录
 *
 * @param data 登录参数（用户名、密码）
 * @returns 登录结果（token + 用户信息）
 */
export function loginApi(data: LoginParams): Promise<ApiResult<LoginResult>> {
  return request.post('/auth/login', data)
}

/**
 * 用户注册
 *
 * @param data 注册参数
 * @returns 空数据
 */
export function registerApi(data: RegisterParams): Promise<ApiResult<null>> {
  return request.post('/auth/register', data)
}

/**
 * 获取当前登录用户信息
 *
 * @returns 当前用户信息
 */
export function getUserInfoApi(): Promise<ApiResult<UserInfo>> {
  return request.get('/users/me')
}

/**
 * 用户登出
 *
 * 说明：当前后端为无状态 JWT 认证，登出仅需前端清理本地 token 即可。
 * 若后续后端加入 token 黑名单（Redis），可在此补充调用。
 */
export function logoutApi(): void {
  // 无后端调用，前端 store 负责清理本地状态
}
