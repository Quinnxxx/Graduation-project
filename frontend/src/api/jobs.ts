/**
 * 校招岗位接口
 *
 * 岗位数据由采集 Agent 写入，本模块仅提供查询与统计。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult, PageResult } from '@/types/api'
import type { JobPosition, JobPositionQuery, JobStats } from '@/types/business'

/**
 * 分页查询校招岗位
 *
 * @param params 分页与筛选条件（关键词、类别、城市、学历、薪资、状态等）
 * @returns 岗位分页结果
 */
export function pageJobs(
  params: JobPositionQuery,
): Promise<ApiResult<PageResult<JobPosition>>> {
  return request.get('/jobs/page', { params })
}

/**
 * 查询岗位详情
 *
 * @param id 岗位 ID（雪花 ID 以字符串承载，兼容 number 入参）
 * @returns 岗位完整信息
 */
export function getJobDetail(id: number | string): Promise<ApiResult<JobPosition>> {
  return request.get(`/jobs/${id}`)
}

/**
 * 校招岗位统计（在招总数、类别分布、城市 Top10）
 *
 * @returns 岗位统计结果
 */
export function getJobStats(): Promise<ApiResult<JobStats>> {
  return request.get('/jobs/stats')
}
