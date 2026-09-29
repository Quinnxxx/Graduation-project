/**
 * 用户求职画像接口
 *
 * 每个用户一条画像，POST 接口为创建/更新（upsert）幂等语义。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult } from '@/types/api'
import type { UserProfile, UserProfileSaveParams } from '@/types/business'

/**
 * 获取当前登录用户画像
 *
 * 尚未填写画像时，后端返回的 data 为 null（由前端引导填写）。
 *
 * @returns 用户画像，未填写时为 null
 */
export function getMyProfile(): Promise<ApiResult<UserProfile | null>> {
  return request.get('/profile/me')
}

/**
 * 创建或更新当前登录用户画像
 *
 * @param data 画像保存参数（字段级更新，未传字段保持原值；skillTags 传 [] 清空标签）
 * @returns 保存后的用户画像
 */
export function saveMyProfile(
  data: UserProfileSaveParams,
): Promise<ApiResult<UserProfile>> {
  return request.post('/profile/me', data)
}
