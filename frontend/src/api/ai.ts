/**
 * AI 服务转发接口（非流式）
 *
 * 前端统一经 business-service 转发至 ai-agent-service：
 * business-service 从用户 JWT 注入 user_id，并附加内部令牌，前端无需感知 AI 服务地址。
 *
 * 说明：SSE 流式对话（/ai/chat/stream）不在本模块，由专门的 composable 承载。
 */

import request from './request'

import type { ApiResult } from '@/types/api'
import type { AiChatParams, AiChatResult } from '@/types/business'

/**
 * AI 对话（非流式）
 *
 * AI 深度推理（岗位分析、简历优化、模拟面试等）单次耗时可达 2 分钟以上，
 * 故单独将超时放宽至 300s，避免被 request 实例全局 15s 超时误杀。
 *
 * @param data 对话参数（query 必填，可带 sessionId/resumeText）
 * @returns AI 回复结果（agentName、finalResponse、error）
 */
export function chat(data: AiChatParams): Promise<ApiResult<AiChatResult>> {
  return request.post('/ai/chat', data, { timeout: 300000 })
}
