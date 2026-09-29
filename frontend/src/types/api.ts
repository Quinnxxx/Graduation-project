/**
 * 全局类型定义
 *
 * 与后端 business-service 统一返回结构对齐：
 * { code, msg, data }
 */

/** 后端统一响应结构 */
export interface ApiResult<T = unknown> {
  /** 状态码：200 成功，其他为业务错误 */
  code: number
  /** 提示信息 */
  msg: string
  /** 业务数据 */
  data: T
}

/** 分页响应结构 */
export interface PageResult<T> {
  /** 总记录数 */
  total: number
  /** 当前页码 */
  pageNum: number
  /** 每页条数 */
  pageSize: number
  /** 当前页数据 */
  list: T[]
}

/** 分页查询参数 */
export interface PageQuery {
  /** 页码，默认 1 */
  pageNum?: number
  /** 每页条数，默认 10 */
  pageSize?: number
}
