/**
 * Axios 统一请求封装
 *
 * 能力：
 * - 请求拦截器：自动携带 token（Authorization: Bearer xxx）
 * - 响应拦截器：统一解包 ApiResult、业务错误统一 message 提示、401 自动登出跳转
 * - 支持取消请求（createAbortController）
 */

import axios from 'axios'
import type { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import JSONBig from 'json-bigint'
import { message } from 'ant-design-vue'

import router from '@/router'
import type { ApiResult } from '@/types/api'
import { getToken, removeToken, removeUserInfo } from '@/utils/storage'

/** 业务成功状态码（与后端 ResultCode.SUCCESS 对齐） */
const SUCCESS_CODE = 200

/** 未授权状态码（与后端 ResultCode.UNAUTHORIZED 对齐） */
const UNAUTHORIZED_CODE = 401

/**
 * 大整数安全的 JSON 解析器。
 *
 * 后端雪花算法主键为 18 位 BIGINT，超出 JS Number.MAX_SAFE_INTEGER，
 * 原生 JSON.parse 会丢失末位精度，导致按 id 查询详情等场景失效；
 * storeAsString 仅把超出安全整数范围的数字解析为字符串，
 * 普通数值（分页 total、计数、薪资、评分等）仍保持 number。
 */
const jsonBig = JSONBig({ storeAsString: true })

/**
 * 自定义响应体解析：用 json-bigint 替代 axios 默认的 JSON.parse；
 * 非字符串 / 空响应 / 解析失败时原样返回，交由后续逻辑处理。
 *
 * @param data 原始响应体
 * @returns 解析后的对象或原始响应体
 */
function parseResponse(data: unknown): unknown {
  if (typeof data !== 'string' || data.length === 0) {
    return data
  }
  try {
    return jsonBig.parse(data)
  } catch {
    return data
  }
}

/**
 * 创建 axios 实例
 *
 * baseURL 从环境变量读取，VITE_API_BASE_URL 由 .env 文件或构建参数注入
 */
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  // 覆盖默认 JSON.parse，避免雪花 ID 精度丢失
  transformResponse: [parseResponse],
})

/**
 * 请求拦截器：自动携带 token
 *
 * @param config 请求配置
 * @returns 携带 token 后的请求配置
 */
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  },
)

/**
 * 响应拦截器：统一处理业务状态码与 HTTP 错误
 *
 * 成功时直接解包返回 response.data（即 ApiResult<T>），
 * 调用方无需再访问 res.data.data。
 */
service.interceptors.response.use(
  (response: AxiosResponse<ApiResult>) => {
    const res = response.data

    // 业务成功：直接返回解包后的 ApiResult
    if (res.code === SUCCESS_CODE) {
      return res as unknown as AxiosResponse
    }

    // 登录失效：清理本地凭证并跳转登录页
    if (res.code === UNAUTHORIZED_CODE) {
      clearAuthAndRedirect()
      return Promise.reject(new Error(res.msg || '登录已过期，请重新登录'))
    }

    // 业务错误：统一提示
    message.error(res.msg || '请求失败')
    return Promise.reject(new Error(res.msg || '请求失败'))
  },
  (error: AxiosError<ApiResult>) => {
    // HTTP 层错误处理
    if (error.response?.status === 401) {
      clearAuthAndRedirect()
    }
    const msg = error.response?.data?.msg || error.message || '网络异常，请稍后重试'
    // 取消请求不提示
    if (!axios.isCancel(error)) {
      message.error(msg)
    }
    return Promise.reject(error)
  },
)

/**
 * 清理本地认证信息并跳转登录页
 */
function clearAuthAndRedirect(): void {
  removeToken()
  removeUserInfo()
  const current = router.currentRoute.value
  if (current.path !== '/login') {
    router.push({ path: '/login', query: { redirect: current.fullPath } })
  }
}

/**
 * 创建取消请求控制器（AbortController 封装）
 *
 * 用法：const controller = createAbortController();
 *       request.get('/xxx', { signal: controller.signal });
 *       controller.abort();  // 取消请求
 *
 * @returns AbortController 实例
 */
export function createAbortController(): AbortController {
  return new AbortController()
}

export default service
