/**
 * 用户状态模块
 *
 * 管理 token、用户信息，提供登录 / 登出 / 拉取用户信息动作。
 * token 同时持久化到 localStorage，刷新页面不丢失登录态。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { getUserInfoApi, loginApi } from '@/api/auth'
import type { LoginParams, UserInfo } from '@/types/user'
import { getToken, getUserInfo, removeToken, removeUserInfo, setToken, setUserInfo } from '@/utils/storage'

/**
 * 用户 Store
 *
 * @returns 用户状态与动作
 */
export const useUserStore = defineStore('user', () => {
  /** 访问令牌（初始化时从本地存储恢复） */
  const token = ref<string>(getToken())

  /** 用户信息（初始化时从本地存储恢复，null 表示未加载） */
  const userInfo = ref<UserInfo | null>(getUserInfo<UserInfo>())

  /**
   * 登录：调用登录接口，保存 token 与用户信息
   *
   * @param params 登录参数
   * @returns 登录结果
   */
  async function login(params: LoginParams): Promise<UserInfo> {
    const res = await loginApi(params)
    token.value = res.data.token
    userInfo.value = res.data.user
    setToken(res.data.token)
    setUserInfo(res.data.user)
    return res.data.user
  }

  /**
   * 拉取当前登录用户信息并刷新本地缓存
   */
  async function fetchUserInfo(): Promise<UserInfo> {
    const res = await getUserInfoApi()
    userInfo.value = res.data
    setUserInfo(res.data)
    return res.data
  }

  /**
   * 登出：清理 token 与用户信息（前端清理凭证）
   */
  function logout(): void {
    resetState()
  }

  /**
   * 重置用户状态并清理本地存储
   */
  function resetState(): void {
    token.value = ''
    userInfo.value = null
    removeToken()
    removeUserInfo()
  }

  return {
    token,
    userInfo,
    login,
    fetchUserInfo,
    logout,
    resetState,
  }
})
