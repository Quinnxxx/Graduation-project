/**
 * 能力画像接口
 *
 * 数据由面试复盘 Agent 在面试结束后写入，业务服务提供查询能力。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult } from '@/types/api'
import type { AbilityProfile, AbilityTrendPoint } from '@/types/business'

/**
 * 查询我的最新能力画像（各维度最新快照）
 *
 * @returns 各能力维度的最新快照列表
 */
export function getMyAbility(): Promise<ApiResult<AbilityProfile[]>> {
  return request.get('/abilities/mine')
}

/**
 * 查询指定维度的能力成长曲线
 *
 * @param dimension 能力维度（必填），如 专业基础/工程实践/算法与数据结构/框架与中间件/软素养
 * @returns 按快照日期正序排列的成长曲线数据点列表
 */
export function getAbilityTrend(
  dimension: string,
): Promise<ApiResult<AbilityTrendPoint[]>> {
  return request.get('/abilities/trend', { params: { dimension } })
}

/**
 * 写入我的能力画像快照（单维度写入）
 *
 * 复盘报告生成后按 ABILITY_DIMENSIONS 五维各写一条；
 * dimension 必须为标准能力维度（@NotBlank），dimensionScore 0-100 整数
 * （@NotNull）；evaluation / snapshotDate 可选（snapshotDate 缺省当天）。
 * 越权 / 身份异常由 request.ts 统一拦截提示。
 *
 * @param params 单维度写入参数
 * @returns 写入后的能力画像快照
 */
export function saveAbility(params: {
  dimension: string
  dimensionScore: number
  evaluation?: string
  snapshotDate?: string
}): Promise<ApiResult<AbilityProfile>> {
  return request.post('/abilities', params)
}
