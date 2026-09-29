/**
 * SSE 流式对话 composable
 *
 * 为什么不用原生 EventSource：
 * EventSource 仅支持 GET 请求，且无法自定义请求头；而 AI 流式接口是 POST，
 * 并必须携带 `Authorization: Bearer <token>` 鉴权头，因此这里采用
 * fetch + ReadableStream 手写 SSE 解析。
 *
 * 链路：前端 -> business-service（/api/ai/chat/stream，vite proxy 剥离 /api）
 *      -> ai-agent-service。SSE 帧经 Spring SseEmitter 转发后，data 前缀可能是
 * "data:"（无空格）或 "data:"（有空格），解析对两种形式均兼容；同时正确处理
 * TCP 半包（残片缓存）与粘包（一次多行）。
 *
 * 事件帧 payload 结构：{ "type": "meta|chunk|final|error", "data": unknown }。
 */

import { ref } from 'vue'
import type { Ref } from 'vue'

import router from '@/router'
import type { AiChatParams } from '@/types/business'
import { getToken, removeToken, removeUserInfo } from '@/utils/storage'

/** meta 事件数据（路由意图与实际处理 Agent） */
interface StreamMeta {
  /** 意图标识：job/resume/tech/hr/chat */
  intent: string
  /** 实际处理 Agent 名 */
  agent: string
}

/** SSE 事件帧 */
interface StreamEvent {
  /** 事件类型 */
  type: 'meta' | 'chunk' | 'final' | 'error'
  /** 事件负载（meta 为对象，chunk/final/error 为字符串） */
  data: unknown
}

/** 流式回调集合（均可选） */
export interface UseChatStreamHandlers {
  /** 收到 meta 帧（意图与 Agent 信息） */
  onMeta?: (data: StreamMeta) => void
  /** 收到增量文本块 */
  onChunk?: (text: string) => void
  /** 收到 final 帧（完整文本，以此为准） */
  onFinal?: (fullText: string) => void
  /** 收到 error 帧或发生错误 */
  onError?: (message: string) => void
}

/** composable 返回值 */
export interface UseChatStreamReturn {
  /** 是否正在流式接收 */
  isStreaming: Ref<boolean>
  /** 已接收的完整文本 */
  fullText: Ref<string>
  /** 发起一次流式对话 */
  send: (params: AiChatParams) => Promise<void>
  /** 主动中止当前流式请求 */
  stop: () => void
}

/**
 * 清理本地登录凭证并跳转登录页（与 request.ts 拦截器的 401 处理保持一致）
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
 * 创建 SSE 流式对话控制器
 *
 * @param handlers 各事件回调（onMeta/onChunk/onFinal/onError）
 * @returns 响应式状态与 send/stop 方法
 */
export function useChatStream(handlers: UseChatStreamHandlers = {}): UseChatStreamReturn {
  /** 是否正在流式接收 */
  const isStreaming = ref(false)
  /** 已接收的完整文本 */
  const fullText = ref('')
  /** 当前请求的中止控制器 */
  let controller: AbortController | null = null

  /**
   * 逐行解析并分发 SSE 事件
   *
   * 兼容 "data:" 与 "data: " 前缀；半包通过 buffer 残片缓存、粘包通过按行拆分处理；
   * 单行 JSON 解析失败仅告警跳过，不中断整个流。
   *
   * @param body 响应可读流
   */
  async function consumeStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finished = false

    while (!finished) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })

      // 按换行拆分；最后一段为残片（buffer 不以 \n 结尾时），保留至下一轮拼接
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const rawLine of lines) {
        const line = rawLine.trim()
        // SSE 数据行以 data 开头且必须含冒号
        if (!line.startsWith('data') || !line.includes(':')) {
          continue
        }
        const colonIndex = line.indexOf(':')
        const payload = line.slice(colonIndex + 1).trim()
        if (!payload) {
          continue
        }

        let event: StreamEvent
        try {
          event = JSON.parse(payload) as StreamEvent
        } catch {
          // 单帧解析失败不影响后续帧
          console.warn('[useChatStream] SSE 数据帧解析失败:', payload)
          continue
        }

        switch (event.type) {
          case 'meta':
            handlers.onMeta?.(event.data as StreamMeta)
            break
          case 'chunk': {
            const text = String(event.data ?? '')
            fullText.value += text
            handlers.onChunk?.(text)
            break
          }
          case 'final': {
            const text = String(event.data ?? '')
            // 以 final 完整文本为准，覆盖增量拼接结果
            fullText.value = text
            handlers.onFinal?.(text)
            finished = true
            break
          }
          case 'error':
            handlers.onError?.(String(event.data ?? 'AI 服务错误'))
            finished = true
            break
          default:
            break
        }

        if (finished) {
          break
        }
      }
    }
  }

  /**
   * 发起流式对话
   *
   * @param params 对话参数（query 必填，可带 sessionId/resumeText）
   */
  async function send(params: AiChatParams): Promise<void> {
    const token = getToken()
    if (!token) {
      handlers.onError?.('未登录')
      return
    }

    controller = new AbortController()
    isStreaming.value = true
    fullText.value = ''

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/ai/chat/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(params),
          signal: controller.signal,
        },
      )

      if (!response.ok) {
        if (response.status === 401) {
          clearAuthAndRedirect()
        } else {
          handlers.onError?.(`服务异常 ${response.status}`)
        }
        return
      }

      if (!response.body) {
        handlers.onError?.('响应流为空')
        return
      }

      await consumeStream(response.body)
    } catch (error) {
      // 用户主动中止：静默处理，不弹错误
      if ((error as Error)?.name === 'AbortError') {
        return
      }
      console.error('[useChatStream] 流式请求异常:', error)
      handlers.onError?.('网络异常，请重试')
    } finally {
      isStreaming.value = false
    }
  }

  /**
   * 主动停止流式接收
   */
  function stop(): void {
    controller?.abort()
    isStreaming.value = false
  }

  return { isStreaming, fullText, send, stop }
}
