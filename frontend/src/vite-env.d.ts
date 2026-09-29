/**
 * Vite 客户端类型声明与环境变量类型
 */

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 应用标题 */
  readonly VITE_APP_TITLE: string
  /** 后端业务服务地址 */
  readonly VITE_API_BASE_URL: string
  /** AI Agent 服务地址 */
  readonly VITE_AI_AGENT_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
