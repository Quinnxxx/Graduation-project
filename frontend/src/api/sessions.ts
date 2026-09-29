/**
 * 用户会话接口
 *
 * 会话记录仅能访问当前登录用户本人的数据（后端按 userId 过滤与归属校验）。
 * 注意：后端未提供会话详情端点（GET /sessions/{id}），列表即完整数据。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult, PageResult } from '@/types/api'
import type {
  SessionPageParams,
  SessionRecord,
  SessionSaveParams,
  SessionUpdateParams,
} from '@/types/business'

/**
 * 分页查询我的会话记录
 *
 * @param params 分页参数（可按 sessionType 筛选）
 * @returns 会话记录分页结果（按创建时间倒序）
 */
export function pageSessions(
  params: SessionPageParams,
): Promise<ApiResult<PageResult<SessionRecord>>> {
  return request.get('/sessions/page', { params })
}

/**
 * 创建用户会话
 *
 * @param data 创建参数（会话类型必填，标题为空时后端默认“新建会话”）
 * @returns 创建后的会话记录
 */
export function createSession(
  data: SessionSaveParams,
): Promise<ApiResult<SessionRecord>> {
  return request.post('/sessions', data)
}

/**
 * 更新用户会话（标题/摘要/状态）
 *
 * @param id   会话 ID
 * @param data 更新参数（仅对显式传值的字段生效）
 * @returns 更新后的会话记录
 */
export function updateSession(
  id: number,
  data: SessionUpdateParams,
): Promise<ApiResult<SessionRecord>> {
  return request.put(`/sessions/${id}`, data)
}

/**
 * 删除用户会话（逻辑删除）
 *
 * @param id 会话 ID
 * @returns 空数据
 */
export function deleteSession(id: number): Promise<ApiResult<null>> {
  return request.delete(`/sessions/${id}`)
}
