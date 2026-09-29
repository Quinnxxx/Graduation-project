/**
 * 简历记录接口
 *
 * 简历记录仅能访问当前登录用户本人的数据（后端按 userId 过滤与归属校验）。
 * 统一返回 Promise<ApiResult<T>>，调用方通过 res.data 获取业务数据。
 */

import request from './request'

import type { ApiResult, PageResult } from '@/types/api'
import type {
  ResumePageParams,
  ResumeRecord,
  ResumeSaveParams,
  ResumeUpdateParams,
  ResumeUploadResult,
} from '@/types/business'

/**
 * 分页查询我的简历记录
 *
 * @param params 分页参数
 * @returns 简历记录分页结果（按创建时间倒序）
 */
export function pageResumes(
  params: ResumePageParams,
): Promise<ApiResult<PageResult<ResumeRecord>>> {
  return request.get('/resumes/page', { params })
}

/**
 * 上传 PDF 简历（校验、落盘并提取文本，不落库）
 *
 * 上传成功后由前端把 fileName/filePath/fileSize/text 填入创建表单，
 * 再调 createResume 随创建请求回传。FormData 上传，Content-Type 由浏览器自动设置。
 *
 * @param file PDF 文件（≤5MB）
 * @returns 上传结果（fileName / fileSize / filePath / text）
 */
export function uploadResumePdf(file: File): Promise<ApiResult<ResumeUploadResult>> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/resumes/upload', formData)
}

/**
 * 创建简历记录
 *
 * @param data 创建参数（标题、原始简历内容、目标岗位）
 * @returns 创建后的简历记录
 */
export function createResume(
  data: ResumeSaveParams,
): Promise<ApiResult<ResumeRecord>> {
  return request.post('/resumes', data)
}

/**
 * 查询简历记录详情
 *
 * @param id 简历记录 ID
 * @returns 简历记录详情
 */
export function getResumeDetail(id: number): Promise<ApiResult<ResumeRecord>> {
  return request.get(`/resumes/${id}`)
}

/**
 * 更新简历记录（AI 优化回填）
 *
 * @param id   简历记录 ID
 * @param data 更新参数（仅对显式传值的字段生效）
 * @returns 更新后的简历记录
 */
export function updateResume(
  id: number,
  data: ResumeUpdateParams,
): Promise<ApiResult<ResumeRecord>> {
  return request.put(`/resumes/${id}`, data)
}

/**
 * 删除简历记录（逻辑删除）
 *
 * @param id 简历记录 ID
 * @returns 空数据
 */
export function deleteResume(id: number): Promise<ApiResult<null>> {
  return request.delete(`/resumes/${id}`)
}
