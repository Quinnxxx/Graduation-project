/**
 * 模拟面试接口
 *
 * 面试记录仅能访问当前登录用户本人的数据（后端按 userId 过滤与归属校验）。
 * 对话消息不提供独立列表端点：消息在“面试详情”接口的 messages 字段中一并返回。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult, PageResult } from '@/types/api'
import type {
  InterviewCreateParams,
  InterviewMessage,
  InterviewPageParams,
  InterviewRecord,
  InterviewUpdateParams,
  MessageAppendParams,
} from '@/types/business'

/**
 * 分页查询我的面试记录
 *
 * @param params 分页参数（可按 interviewType 筛选）
 * @returns 面试记录分页结果（列表项不含 messages，按创建时间倒序）
 */
export function pageInterviews(
  params: InterviewPageParams,
): Promise<ApiResult<PageResult<InterviewRecord>>> {
  return request.get('/interviews/page', { params })
}

/**
 * 创建模拟面试
 *
 * @param data 创建参数（面试类型必填，难度默认 2 中等）
 * @returns 创建后的面试记录
 */
export function createInterview(
  data: InterviewCreateParams,
): Promise<ApiResult<InterviewRecord>> {
  return request.post('/interviews', data)
}

/**
 * 查询面试详情（含对话消息）
 *
 * @param id 面试记录 ID
 * @returns 面试记录详情，messages 字段为按时间正序的对话消息
 */
export function getInterviewDetail(
  id: number | string,
): Promise<ApiResult<InterviewRecord>> {
  return request.get(`/interviews/${id}`)
}

/**
 * 更新面试记录（结束回填：时长、提问数、评分、复盘报告、状态）
 *
 * @param id   面试记录 ID
 * @param data 更新参数（仅对显式传值的字段生效）
 * @returns 更新后的面试记录（不含 messages）
 */
export function updateInterview(
  id: number | string,
  data: InterviewUpdateParams,
): Promise<ApiResult<InterviewRecord>> {
  return request.put(`/interviews/${id}`, data)
}

/**
 * 追加面试消息
 *
 * 仅当面试处于“进行中”状态时可追加；question 类型消息会使后端提问数自增。
 *
 * @param id   面试记录 ID
 * @param data 消息参数（role/messageType/content，点评可带 score）
 * @returns 新创建的消息
 */
export function appendInterviewMessage(
  id: number | string,
  data: MessageAppendParams,
): Promise<ApiResult<InterviewMessage>> {
  return request.post(`/interviews/${id}/messages`, data)
}

/**
 * 删除面试记录（逻辑删除记录并物理删除其消息）
 *
 * @param id 面试记录 ID
 * @returns 空数据
 */
export function deleteInterview(id: number | string): Promise<ApiResult<null>> {
  return request.delete(`/interviews/${id}`)
}
