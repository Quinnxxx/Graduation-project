<script setup lang="ts">
/**
 * AI 求职助手（前端核心页面）
 *
 * 左栏：会话列表（session_record 元信息）的查询、新建、重命名、删除；
 * 右栏：场景切换、消息气泡（user / assistant）、SSE token 级流式接收、
 * 附带简历文本与输入区。
 *
 * 设计取舍（务必知悉）：
 * - 普通对话消息不做前端持久化，后端 session_record 仅记录会话元信息
 *   （无消息明细表），因此历史会话不提供逐句回放，仅展示摘要；
 * - 模拟面试的完整问答在“模拟面试”模块承载；
 * - 用户私有简历文本仅在当次请求中透传给 AI，不落地存储。
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { message } from 'ant-design-vue'
import type { Component } from 'vue'
import {
  CodeOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PaperClipOutlined,
  PlusOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'

import MdContent from '@/components/MdContent.vue'
import { useChatStream } from '@/composables/useChatStream'
import { createResume, getResumeDetail, pageResumes, updateResume } from '@/api/resumes'
import {
  createSession,
  deleteSession,
  pageSessions,
  updateSession,
} from '@/api/sessions'
import type { ResumeRecord, SessionRecord } from '@/types/business'

const route = useRoute()
const router = useRouter()

/* --------------------------------- 类型定义 -------------------------------- */

/** 聊天消息（仅前端运行态，不持久化） */
interface ChatMessage {
  /** 前端生成的唯一 id */
  id: string
  /** 消息角色 */
  role: 'user' | 'assistant'
  /** 消息文本（assistant 为 Markdown） */
  content: string
  /** 实际处理 Agent：job/resume/tech/hr/chat */
  agent?: string
  /** 是否正在流式生成 */
  streaming?: boolean
  /** 是否发生错误 */
  error?: boolean
  /** 简历优化结构化结果（解析自报告末尾结果块；缺失即未产出） */
  optimizeResult?: {
    /** 优化后的完整简历全文（可直接替换原全文） */
    optimizedContent: string
    /** 优化要点列表 */
    suggestions: string[]
    /** 优化前评分 0-100（缺省时不展示） */
    resumeScore?: number
    /** 优化后评分 0-100（缺省时不展示） */
    optimizedScore?: number
  }
  /** 该结果是否已落库（落库后按钮隐藏/置灰） */
  optimizeSaved?: boolean
}

/** Agent 展示元信息（中文名 + 标签色） */
const AGENT_META: Record<string, { label: string; color: string }> = {
  job: { label: '岗位匹配顾问', color: 'blue' },
  resume: { label: '简历优化专家', color: 'green' },
  tech: { label: '技术面试官', color: 'orange' },
  hr: { label: 'HR面试官', color: 'purple' },
  chat: { label: 'AI助手', color: 'default' },
}

/** intent → session_record.session_type 映射 */
const INTENT_SESSION_TYPE: Record<string, number> = {
  job: 1,
  resume: 2,
  tech: 3,
  hr: 3,
  chat: 5,
}

/** 会话类型展示元信息 */
const SESSION_TYPE_META: Record<number, { label: string; color: string }> = {
  1: { label: '岗位匹配', color: 'blue' },
  2: { label: '简历优化', color: 'green' },
  3: { label: '模拟面试', color: 'orange' },
  4: { label: '能力复盘', color: 'cyan' },
  5: { label: '自由问答', color: 'default' },
}

/**
 * 获取 Agent 元信息，未知值兜底为 chat。
 *
 * @param agent Agent 名
 * @returns 展示元信息
 */
function agentMeta(agent?: string): { label: string; color: string } {
  return AGENT_META[agent ?? 'chat'] ?? AGENT_META.chat
}

/**
 * 获取会话类型元信息。
 *
 * @param type session_type
 * @returns 展示元信息
 */
function sessionTypeMeta(type?: number): { label: string; color: string } {
  return SESSION_TYPE_META[type ?? 5] ?? SESSION_TYPE_META[5]
}

/* ------------------------------ 流式控制器接入 ----------------------------- */

/**
 * 生成前端消息唯一 id。
 *
 * @returns 字符串 id
 */
function uid(): string {
  return `m_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

/** 最后一条 assistant 消息（流式占位始终在末尾） */
function lastAssistant(): ChatMessage | undefined {
  const list = messages.value
  for (let i = list.length - 1; i >= 0; i--) {
    if (list[i].role === 'assistant') {
      return list[i]
    }
  }
  return undefined
}

/**
 * 按结果块标记切分报告：标记前为用户可见的 Markdown 报告，标记后为机器可读 JSON。
 *
 * @param text 完整回复文本
 * @returns 切分结果（无标记时 display 为原文、jsonText 为 null）
 */
function splitOptimizeBlock(text: string): { display: string; jsonText: string | null } {
  const marker = '<!--RESUME_OPTIMIZE_RESULT-->'
  const idx = text.indexOf(marker)
  if (idx === -1) {
    return { display: text, jsonText: null }
  }
  return {
    display: text.slice(0, idx).trimEnd(),
    jsonText: text.slice(idx + marker.length),
  }
}

/**
 * 容错解析结果块：取 ```json 围栏内容 → JSON.parse → 映射驼峰字段。
 *
 * 容错铁律：标记缺失 / 围栏缺失 / 解析失败 / optimized_content 缺失
 * → 返回 undefined（页面仅缺操作区，不报错、不中断对话）。
 *
 * @param text 完整回复文本
 * @returns 解析结果或 undefined
 */
function parseOptimizeResult(text: string): ChatMessage['optimizeResult'] {
  try {
    const { jsonText } = splitOptimizeBlock(text)
    if (!jsonText) {
      return undefined
    }
    const fence = jsonText.match(/```json\s*([\s\S]*?)```/)
    const raw = fence ? fence[1].trim() : jsonText.trim()
    const data = JSON.parse(raw)
    if (typeof data.optimized_content !== 'string' || data.optimized_content.length === 0) {
      return undefined
    }
    return {
      optimizedContent: data.optimized_content,
      suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
      resumeScore: typeof data.resume_score === 'number' ? data.resume_score : undefined,
      optimizedScore: typeof data.optimized_score === 'number' ? data.optimized_score : undefined,
    }
  } catch {
    return undefined
  }
}

/**
 * 完成态消息收尾：剥离结果块展示 + 容错解析结果块。
 *
 * @param last 目标 assistant 消息
 * @param full 完整回复文本
 */
function applyAssistantFinal(last: ChatMessage, full: string): void {
  last.content = splitOptimizeBlock(full).display
  last.optimizeResult = parseOptimizeResult(full)
  last.streaming = false
}

const stream = useChatStream({
  onMeta: (data) => {
    const last = lastAssistant()
    if (last) {
      last.agent = data.agent
    }
    currentAgent.value = data.agent
    // 首轮：会话尚未落库，按意图创建 session_record
    if (currentSessionId.value === null) {
      void createSessionFromMeta(data.agent)
    }
  },
  onChunk: (text) => {
    const last = lastAssistant()
    if (last) {
      last.content += text
      // 流式期间也不展示结果块，避免 JSON 一闪而过
      last.content = splitOptimizeBlock(last.content).display
    }
    autoScroll()
  },
  onFinal: (full) => {
    const last = lastAssistant()
    if (last) {
      applyAssistantFinal(last, full ?? '')
    }
    autoScroll()
    // 首轮创建的会话：异步回填摘要（失败静默，不阻断对话）
    if (currentSessionId.value !== null) {
      void updateSessionSummary(currentSessionId.value, full)
    }
  },
  onError: (msg) => {
    const last = lastAssistant()
    if (last) {
      last.streaming = false
      last.error = true
      // 无任何已生成文本时，直接以错误文案作为内容
      if (!last.content) {
        last.content = msg
      }
    }
  },
})

const { isStreaming, fullText, send: streamSend, stop: streamStop } = stream

/* --------------------------------- 会话状态 -------------------------------- */

/** 当前会话 id（首轮 meta 后回填；历史视图为查看项 id） */
const currentSessionId = ref<number | null>(null)
/** 右栏当前标题 */
const currentTitle = ref('新会话')
/** 当前 Agent（用于顶栏 tag） */
const currentAgent = ref('')
/** 右栏视图：chat 对话态 / history 历史会话摘要态 */
const viewMode = ref<'chat' | 'history'>('chat')
/** 历史视图查看的会话 */
const historySession = ref<SessionRecord | null>(null)

/** 运行态消息列表 */
const messages = ref<ChatMessage[]>([])
/** 输入框文本 */
const inputText = ref('')
/** 附带简历文本 */
const resumeText = ref('')
/** 附带简历弹窗显隐 */
const resumeModalOpen = ref(false)
/** 所选简历记录 ID（审核操作区"替换原简历"用；未选为 null） */
const selectedResumeId = ref<number | null>(null)
/** 所选简历标题 */
const selectedResumeTitle = ref('')
/** 所选简历目标岗位（另存新简历时带入） */
const selectedResumeTargetPosition = ref('')
/** 简历下拉选项列表（弹窗选择用，最多前 100 条） */
const resumeList = ref<ResumeRecord[]>([])
/** 简历下拉加载中 */
const resumeOptionsLoading = ref(false)

/** 简历下拉选项（value=记录ID，label=标题+创建时间） */
const resumeOptions = computed(() =>
  resumeList.value.map((r) => ({
    value: r.id,
    label: `${r.resumeTitle}（${fmtTime(r.createTime)}）`,
  })),
)

/**
 * 加载简历下拉选项（前 100 条）；失败置空并提示，不阻断对话。
 */
async function loadResumeOptions(): Promise<void> {
  resumeOptionsLoading.value = true
  try {
    const res = await pageResumes({ pageNum: 1, pageSize: 100 })
    resumeList.value = res.data?.list ?? []
  } catch (error) {
    console.warn('[assistant] 简历选项加载失败:', error)
    resumeList.value = []
  } finally {
    resumeOptionsLoading.value = false
  }
}

/**
 * 打开附带简历弹窗并刷新简历下拉选项。
 */
function openResumeModal(): void {
  resumeModalOpen.value = true
  void loadResumeOptions()
}

/**
 * 选择简历：按 id 拉取详情填充 resumeText（优化后优先），并记录所选简历信息。
 *
 * @param id 所选简历记录 ID（清空时为 undefined）
 */
async function handleResumeSelect(id?: number): Promise<void> {
  if (!id) {
    selectedResumeId.value = null
    selectedResumeTitle.value = ''
    selectedResumeTargetPosition.value = ''
    return
  }
  try {
    const res = await getResumeDetail(id)
    const detail = res.data
    resumeText.value = detail?.optimizedContent || detail?.originalContent || ''
    selectedResumeId.value = id
    selectedResumeTitle.value = detail?.resumeTitle || ''
    selectedResumeTargetPosition.value = detail?.targetPositionName || ''
  } catch (error) {
    console.warn('[assistant] 简历详情加载失败:', error)
  }
}

/**
 * 清空简历附带状态（标签 × 清除与落库成功后共用）。
 */
function resetResumeAttachment(): void {
  resumeText.value = ''
  selectedResumeId.value = null
  selectedResumeTitle.value = ''
  selectedResumeTargetPosition.value = ''
}

/**
 * 附带简历弹窗"确定"：简历文本非空则关闭弹窗并发起优化，为空则提示并保持弹窗。
 */
async function handleResumeOk(): Promise<void> {
  if (!resumeText.value.trim()) {
    message.warning('请先选择或粘贴简历内容')
    return
  }
  resumeModalOpen.value = false
  await sendMessage('请帮我优化简历')
}

/* ------------------------------- 会话列表（左栏） --------------------------- */

/** 会话列表 */
const sessions = ref<SessionRecord[]>([])
/** 会话列表加载态 */
const sessionsLoading = ref(false)
/** 重命名中的会话 id */
const editingId = ref<number | null>(null)
/** 重命名输入值 */
const editingTitle = ref('')

/** 左栏当前高亮 key（与 currentSessionId 对齐） */
const selectedSessionKeys = ref<string[]>([])

/**
 * 加载会话列表（pageSize 50，后端按创建时间倒序）。
 */
async function loadSessions(): Promise<void> {
  sessionsLoading.value = true
  try {
    const res = await pageSessions({ pageNum: 1, pageSize: 50 })
    sessions.value = res.data?.list ?? []
  } catch (error) {
    console.warn('[assistant] 会话列表加载失败:', error)
    message.error('会话列表加载失败')
  } finally {
    sessionsLoading.value = false
  }
}

/**
 * 新建会话：清空对话态与附带简历，回到新会话。
 * 流式中禁用（按钮 disabled）。
 */
function newSession(): void {
  messages.value = []
  currentSessionId.value = null
  resetResumeAttachment()
  inputText.value = ''
  currentTitle.value = '新会话'
  currentAgent.value = ''
  viewMode.value = 'chat'
  historySession.value = null
  selectedSessionKeys.value = []
}

/**
 * 点击历史会话：切换为历史摘要视图（不逐句回放）。
 *
 * @param item 会话记录
 */
function openSession(item: SessionRecord): void {
  if (isStreaming.value) {
    return
  }
  viewMode.value = 'history'
  historySession.value = item
  currentSessionId.value = item.id
  currentTitle.value = item.title || '新建会话'
  currentAgent.value = item.agentName || ''
  selectedSessionKeys.value = [String(item.id)]
  // 切换会话不携带上一话题的简历文本
  resetResumeAttachment()
}

/**
 * 进入行内重命名。
 *
 * @param item 会话记录
 */
function startRename(item: SessionRecord): void {
  editingId.value = item.id
  editingTitle.value = item.title || ''
}

/**
 * 确认重命名（回车 / 失焦），成功后刷新列表。
 *
 * @param item 会话记录
 */
async function confirmRename(item: SessionRecord): Promise<void> {
  if (editingId.value !== item.id) {
    return
  }
  const title = editingTitle.value.trim()
  editingId.value = null
  if (!title || title === item.title) {
    return
  }
  try {
    await updateSession(item.id, { title })
    if (currentSessionId.value === item.id) {
      currentTitle.value = title
    }
    await loadSessions()
  } catch (error) {
    console.warn('[assistant] 重命名失败:', error)
    message.error('重命名失败')
  }
}

/**
 * 删除会话；若删除的是当前查看项，回到新会话态。
 *
 * @param item 会话记录
 */
async function removeSession(item: SessionRecord): Promise<void> {
  try {
    await deleteSession(item.id)
    if (currentSessionId.value === item.id) {
      newSession()
    }
    await loadSessions()
    message.success('已删除')
  } catch (error) {
    console.warn('[assistant] 删除失败:', error)
    message.error('删除失败')
  }
}

/**
 * 会话时间格式化为 MM-DD HH:mm。
 *
 * @param value 创建时间
 * @returns 短时间文本
 */
function fmtTime(value?: string): string {
  if (!value) {
    return ''
  }
  const d = dayjs(value)
  return d.isValid() ? d.format('MM-DD HH:mm') : ''
}

/* --------------------------- 会话落库（首轮 meta 后） ----------------------- */

/**
 * 首轮 meta：按意图创建 session_record 并回填 currentSessionId。
 *
 * @param agent Agent 名
 */
async function createSessionFromMeta(agent: string): Promise<void> {
  // 标题取本轮首条用户消息，截断 20 字
  let title = '新会话'
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      title = messages.value[i].content.slice(0, 20)
      break
    }
  }
  try {
    const res = await createSession({
      sessionType: INTENT_SESSION_TYPE[agent] ?? 5,
      agentName: agent,
      title,
    })
    currentSessionId.value = res.data.id
    currentTitle.value = res.data.title || title
    selectedSessionKeys.value = [String(res.data.id)]
    await loadSessions()
  } catch (error) {
    // 会话落库失败不影响对话主流程
    console.warn('[assistant] 会话创建失败:', error)
  }
}

/**
 * 首轮会话回填摘要（summary 取回复前 50 字），失败静默。
 *
 * @param id 会话 id
 * @param full 完整回复
 */
async function updateSessionSummary(id: number, full: string): Promise<void> {
  try {
    await updateSession(id, { summary: full.slice(0, 50) })
    await loadSessions()
  } catch (error) {
    console.warn('[assistant] 摘要回填失败:', error)
  }
}

/* --------------------------------- 场景引导 -------------------------------- */

/** 顶部场景按钮 */
const sceneButtons: { scene: string; label: string }[] = [
  { scene: 'job', label: '岗位匹配' },
  { scene: 'resume', label: '简历优化' },
  { scene: 'tech', label: '技术面试' },
  { scene: 'hr', label: 'HR面试' },
  { scene: 'chat', label: '自由问答' },
]

/** 空态欢迎场景大卡片 */
const welcomeScenes: {
  scene: string
  title: string
  desc: string
  icon: Component
}[] = [
  {
    scene: 'job',
    title: '岗位匹配',
    desc: '智能推荐与你匹配的在招岗位',
    icon: RobotOutlined,
  },
  {
    scene: 'resume',
    title: '简历优化',
    desc: 'STAR 法则诊断改写你的简历',
    icon: FileTextOutlined,
  },
  {
    scene: 'tech',
    title: '技术面试',
    desc: '模拟技术面试，实时点评追问',
    icon: CodeOutlined,
  },
  {
    scene: 'hr',
    title: 'HR面试',
    desc: '行为面试与职业规划演练',
    icon: TeamOutlined,
  },
]

/**
 * 场景按钮行为：先新建会话，再按场景自动发送引导语。
 *
 * @param scene 场景标识
 */
async function startScene(scene: string): Promise<void> {
  newSession()
  await nextTick()
  switch (scene) {
    case 'job':
      await sendMessage('帮我推荐合适的校招岗位')
      break
    case 'resume':
      // 仅打开简历选择弹窗，确认后由 handleResumeOk 发起优化
      openResumeModal()
      break
    case 'tech':
      await sendMessage('开始技术面试')
      break
    case 'hr':
      await sendMessage('开始HR面试')
      break
    case 'chat':
    default:
      // 自由问答仅清空并聚焦输入框，不自动发送
      inputText.value = ''
      break
  }
}

/* --------------------------------- 发送 / 停止 ----------------------------- */

/**
 * 发送一条消息并接收流式回复。
 *
 * @param text 指定文本（场景引导 / 重试使用），缺省取输入框
 */
async function sendMessage(text?: string): Promise<void> {
  const content = (text ?? inputText.value).trim()
  if (!content || isStreaming.value) {
    return
  }
  messages.value.push({ id: uid(), role: 'user', content })
  messages.value.push({
    id: uid(),
    role: 'assistant',
    content: '',
    streaming: true,
    agent: undefined,
  })
  inputText.value = ''
  await nextTick()
  scrollToBottom()

  try {
    await streamSend({
      query: content,
      sessionId: currentSessionId.value ? String(currentSessionId.value) : undefined,
      resumeText: resumeText.value || undefined,
    })
  } finally {
    const last = lastAssistant()
    if (last) {
      // 用户中途停止且无增量文本时，用 fullText 兜底
      if (!last.content && fullText.value) {
        last.content = fullText.value
      }
      last.streaming = false
    }
  }
}

/**
 * 停止生成：中止请求并以 fullText 兜底，无内容则标记已停止。
 */
function stopGenerate(): void {
  streamStop()
  const last = lastAssistant()
  if (last) {
    last.streaming = false
    if (fullText.value) {
      applyAssistantFinal(last, fullText.value)
    } else {
      last.error = true
      last.content = '已停止生成'
    }
  }
}

/**
 * 失败重试：移除失败的 assistant 消息，以其对应的用户消息重新发送。
 *
 * @param index 失败 assistant 消息下标
 */
function retryMessage(index: number): void {
  let userContent = ''
  for (let i = index - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      userContent = messages.value[i].content
      break
    }
  }
  messages.value.splice(index, 1)
  if (userContent) {
    void sendMessage(userContent)
  }
}

/* --------------------------- 简历优化结果落库（审核操作区） ------------------- */

/** 落库中按钮标记：'replace' 替换原简历 / 'new' 另存新简历 */
const savingTarget = ref<'replace' | 'new' | null>(null)

/**
 * 替换原简历：把优化稿写回所选简历记录（originalContent 不变，仅更新优化后字段）。
 *
 * @param msg 含优化结果的 assistant 消息
 */
async function saveOptimizeReplace(msg: ChatMessage): Promise<void> {
  if (!msg.optimizeResult || !selectedResumeId.value) {
    return
  }
  savingTarget.value = 'replace'
  try {
    await updateResume(selectedResumeId.value, {
      optimizedContent: msg.optimizeResult.optimizedContent,
      optimizationSuggestions: JSON.stringify(msg.optimizeResult.suggestions),
      resumeScore: msg.optimizeResult.resumeScore,
      optimizedScore: msg.optimizeResult.optimizedScore,
      status: 1,
    })
    message.success('已更新到所选简历')
    msg.optimizeSaved = true
    resetResumeAttachment()
  } catch (error) {
    // 业务错误已由请求层统一提示
    console.warn('[assistant] 替换简历失败:', error)
  } finally {
    savingTarget.value = null
  }
}

/**
 * 另存为新简历：以优化稿作为原始内容新建一条记录（原记录不变）。
 *
 * @param msg 含优化结果的 assistant 消息
 */
async function saveOptimizeNew(msg: ChatMessage): Promise<void> {
  if (!msg.optimizeResult) {
    return
  }
  savingTarget.value = 'new'
  try {
    await createResume({
      resumeTitle: `${selectedResumeTitle.value || '简历'}（AI优化版）`,
      originalContent: msg.optimizeResult.optimizedContent,
      targetPositionName: selectedResumeTargetPosition.value || undefined,
    })
    message.success('已另存为新简历')
    msg.optimizeSaved = true
    resetResumeAttachment()
  } catch (error) {
    // 业务错误已由请求层统一提示
    console.warn('[assistant] 另存简历失败:', error)
  } finally {
    savingTarget.value = null
  }
}

/**
 * 输入框按键：Enter（非 Shift、非中文组词中）发送。
 *
 * @param event 键盘事件
 */
function onInputKeydown(event: KeyboardEvent): void {
  if (
    event.key === 'Enter' &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault()
    void sendMessage()
  }
}

/* ------------------------------ 消息区滚动控制 ----------------------------- */

/** 消息区容器 */
const messageAreaRef = ref<HTMLElement | null>(null)
/** 是否吸附在底部（用户手动上滚后不强制拉下） */
const stickToBottom = ref(true)

/**
 * 消息区滚动事件：更新是否吸附底部（距底部 <120px）。
 */
function onMessageScroll(): void {
  const el = messageAreaRef.value
  if (!el) {
    return
  }
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 120
}

/** 强制滚动到底部（新发送时）。
 */
function scrollToBottom(): void {
  const el = messageAreaRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

/**
 * 流式增量时，仅在吸附底部状态下自动滚动。
 */
function autoScroll(): void {
  if (stickToBottom.value) {
    void nextTick(() => scrollToBottom())
  }
}

/* ------------------------------ 路由 query 联动 ---------------------------- */

/**
 * 处理路由 query（岗位广场“让 AI 分析”等入口跳转），仅处理一次后清除。
 */
async function handleRouteQuery(): Promise<void> {
  const scene = route.query.scene ? String(route.query.scene) : ''
  const keyword = route.query.keyword ? String(route.query.keyword) : ''
  if (!scene) {
    return
  }
  if (scene === 'job' && keyword) {
    newSession()
    await nextTick()
    await sendMessage(`帮我分析这个岗位是否适合我：${keyword}`)
  } else if (scene === 'job' || scene === 'resume' || scene === 'tech' || scene === 'hr') {
    await startScene(scene)
  } else if (scene === 'chat') {
    newSession()
  }
  // 清除 query，避免刷新重复触发
  router.replace({ path: '/assistant', query: {} })
}

onMounted(() => {
  void loadSessions()
  void handleRouteQuery()
})

onBeforeUnmount(() => {
  streamStop()
})
</script>

<template>
  <div class="assistant-wrap">
    <!-- 左栏：会话列表 -->
    <aside class="assistant-sidebar">
      <a-button
        type="primary"
        block
        :disabled="isStreaming"
        @click="newSession"
      >
        <template #icon><PlusOutlined /></template>
        新建会话
      </a-button>

      <div class="session-list">
        <a-spin v-if="sessionsLoading" class="session-spin" />
        <a-empty
          v-else-if="sessions.length === 0"
          description="暂无会话，开始你的第一次咨询"
        />
        <template v-else>
          <div
            v-for="item in sessions"
            :key="item.id"
            class="session-item"
            :class="{ active: currentSessionId === item.id }"
            @click="openSession(item)"
          >
            <a-input
              v-if="editingId === item.id"
              v-model:value="editingTitle"
              size="small"
              @click.stop
              @press-enter="confirmRename(item)"
              @blur="confirmRename(item)"
            />
            <template v-else>
              <div class="session-row">
                <span class="session-title">{{ item.title || '新建会话' }}</span>
                <span class="session-time">{{ fmtTime(item.createTime) }}</span>
              </div>
              <div class="session-meta">
                <a-tag
                  :color="sessionTypeMeta(item.sessionType).color"
                  class="session-type-tag"
                >
                  {{ sessionTypeMeta(item.sessionType).label }}
                </a-tag>
                <span class="session-actions" @click.stop>
                  <EditOutlined
                    class="session-action-icon"
                    title="重命名"
                    @click="startRename(item)"
                  />
                  <a-popconfirm
                    title="确定删除该会话？"
                    @confirm="removeSession(item)"
                  >
                    <DeleteOutlined
                      class="session-action-icon"
                      title="删除"
                      @click.stop
                    />
                  </a-popconfirm>
                </span>
              </div>
            </template>
          </div>
        </template>
      </div>
    </aside>

    <!-- 右栏 -->
    <section class="assistant-main">
      <!-- 顶栏 -->
      <header class="assistant-header">
        <div class="header-left">
          <span class="header-title">{{ currentTitle }}</span>
          <a-tag
            v-if="currentAgent"
            :color="agentMeta(currentAgent).color"
            class="header-agent-tag"
          >
            {{ agentMeta(currentAgent).label }}
          </a-tag>
        </div>
        <div class="header-scenes">
          <a-button
            v-for="btn in sceneButtons"
            :key="btn.scene"
            size="small"
            :disabled="isStreaming"
            @click="startScene(btn.scene)"
          >
            {{ btn.label }}
          </a-button>
        </div>
      </header>

      <!-- 消息区 -->
      <div
        ref="messageAreaRef"
        class="message-area"
        @scroll="onMessageScroll"
      >
        <!-- 历史会话摘要视图 -->
        <div v-if="viewMode === 'history'" class="history-view">
          <a-card class="history-card">
            <div class="history-head">
              <a-typography-title :level="4">
                {{ historySession?.title || '新建会话' }}
              </a-typography-title>
              <a-tag
                :color="sessionTypeMeta(historySession?.sessionType).color"
              >
                {{ sessionTypeMeta(historySession?.sessionType).label }}
              </a-tag>
            </div>
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="会话摘要">
                {{ historySession?.summary || '暂无摘要' }}
              </a-descriptions-item>
              <a-descriptions-item label="创建时间">
                {{ historySession?.createTime || '-' }}
              </a-descriptions-item>
            </a-descriptions>
            <p class="history-tip">
              完整对话由短期记忆实时承载，历史会话不提供逐句回放；
              模拟面试的完整问答请在“模拟面试”模块查看（即将上线）。
            </p>
            <a-button type="primary" @click="newSession">
              基于此话题新建会话
            </a-button>
          </a-card>
        </div>

        <!-- 空态欢迎 -->
        <div v-else-if="messages.length === 0" class="welcome-view">
          <a-typography-title :level="3" class="welcome-heading">
            你好，我是你的校招求职助手
          </a-typography-title>
          <a-row :gutter="16" class="welcome-cards">
            <a-col
              v-for="sc in welcomeScenes"
              :key="sc.scene"
              :xs="24"
              :sm="12"
              :md="6"
            >
              <a-card
                hoverable
                class="welcome-card-item"
                @click="startScene(sc.scene)"
              >
                <component :is="sc.icon" class="welcome-card-icon" />
                <div class="welcome-card-title">{{ sc.title }}</div>
                <div class="welcome-card-desc">{{ sc.desc }}</div>
              </a-card>
            </a-col>
          </a-row>
        </div>

        <!-- 消息气泡 -->
        <div v-else class="messages">
          <template v-for="(msg, index) in messages" :key="msg.id">
            <!-- user -->
            <div v-if="msg.role === 'user'" class="msg-row msg-user">
              <div class="bubble-user">{{ msg.content }}</div>
            </div>
            <!-- assistant -->
            <div v-else class="msg-row msg-assistant">
              <div class="agent-avatar">
                <RobotOutlined />
              </div>
              <div class="bubble-assistant">
                <a-tag
                  v-if="msg.agent"
                  :color="agentMeta(msg.agent).color"
                  class="bubble-agent-tag"
                >
                  {{ agentMeta(msg.agent).label }}
                </a-tag>
                <div v-if="msg.streaming && !msg.content" class="thinking">
                  正在思考...
                </div>
                <MdContent
                  v-if="msg.content"
                  :content="msg.content"
                  :loading="msg.streaming"
                />
                <!-- 简历优化审核操作区（结果块解析成功才渲染） -->
                <template v-if="msg.optimizeResult">
                  <div class="optimize-result">
                    <div
                      v-if="
                        msg.optimizeResult.resumeScore !== undefined ||
                        msg.optimizeResult.optimizedScore !== undefined
                      "
                      class="optimize-score"
                    >
                      评分：优化前 {{ msg.optimizeResult.resumeScore ?? '-' }} →
                      优化后 {{ msg.optimizeResult.optimizedScore ?? '-' }}
                    </div>
                    <div
                      v-if="msg.optimizeResult.suggestions.length > 0"
                      class="optimize-suggestions"
                    >
                      <div class="optimize-suggestions-title">优化要点</div>
                      <a-list
                        size="small"
                        :data-source="msg.optimizeResult.suggestions"
                        class="optimize-suggestions-list"
                      >
                        <template #renderItem="{ item }">
                          <a-list-item class="optimize-suggestion-item">
                            {{ item }}
                          </a-list-item>
                        </template>
                      </a-list>
                    </div>
                    <div class="optimize-actions">
                      <a-button
                        v-if="selectedResumeId && !msg.optimizeSaved"
                        size="small"
                        type="primary"
                        :loading="savingTarget === 'replace'"
                        @click="saveOptimizeReplace(msg)"
                      >
                        替换原简历
                      </a-button>
                      <a-button
                        v-if="!msg.optimizeSaved"
                        size="small"
                        :loading="savingTarget === 'new'"
                        @click="saveOptimizeNew(msg)"
                      >
                        另存为新简历
                      </a-button>
                      <a-tag v-if="msg.optimizeSaved" color="success">已保存</a-tag>
                    </div>
                  </div>
                </template>
                <template v-if="msg.error">
                  <a-alert
                    type="error"
                    show-icon
                    message="回复生成失败或已中断，请重试"
                    class="bubble-alert"
                  />
                  <a-button
                    size="small"
                    class="bubble-retry"
                    @click="retryMessage(index)"
                  >
                    重试
                  </a-button>
                </template>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="composer">
        <div class="composer-tool">
          <a-tag
            v-if="resumeText"
            closable
            color="blue"
            @close="resetResumeAttachment"
          >
            已附带：{{ selectedResumeTitle || '简历文本' }}（点击 × 清除）
          </a-tag>
          <a-button
            v-else
            size="small"
            type="text"
            @click="openResumeModal"
          >
            <template #icon><PaperClipOutlined /></template>
            附带简历
          </a-button>
        </div>
        <div class="composer-row">
          <a-textarea
            v-model:value="inputText"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            @keydown="onInputKeydown"
          />
          <a-button
            v-if="!isStreaming"
            type="primary"
            :disabled="!inputText.trim()"
            @click="sendMessage()"
          >
            发送
          </a-button>
          <a-button v-else danger @click="stopGenerate">
            停止生成
          </a-button>
        </div>
      </footer>
    </section>

    <!-- 附带简历弹窗 -->
    <a-modal
      v-model:open="resumeModalOpen"
      title="选择简历"
      :destroy-on-close="true"
      ok-text="确定"
      cancel-text="取消"
      @ok="handleResumeOk"
    >
      <a-select
        v-model:value="selectedResumeId"
        :options="resumeOptions"
        :loading="resumeOptionsLoading"
        placeholder="选择一份已上传的简历"
        show-search
        option-filter-prop="label"
        allow-clear
        class="resume-picker"
        @change="handleResumeSelect"
      />
      <div v-if="resumeList.length === 0" class="resume-picker-tip">
        暂无简历，请先到「简历」页上传
      </div>
      <a-textarea
        v-model:value="resumeText"
        :rows="12"
        placeholder="选定简历后自动填充原文，也可手动粘贴或微调（兜底入口）"
        class="resume-picker-textarea"
      />
    </a-modal>
  </div>
</template>

<style scoped>
.assistant-wrap {
  display: flex;
  height: calc(100vh - 190px);
  min-height: 480px;
  overflow: hidden;
  background: #fff;
  border-radius: 8px;
}

/* 左栏 */
.assistant-sidebar {
  display: flex;
  flex: 0 0 260px;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #fff;
  border-right: 1px solid #f0f0f0;
}

.session-list {
  flex: 1 1 auto;
  overflow-y: auto;
}

.session-spin {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

.session-item {
  padding: 10px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 8px;
  transition: background 0.2s;
}

.session-item:hover {
  background: #f7faff;
}

.session-item.active {
  background: #eef4ff;
  border-color: #c6dcff;
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.session-title {
  flex: 1 1 auto;
  overflow: hidden;
  font-size: 13px;
  color: #1f2937;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  flex: 0 0 auto;
  font-size: 11px;
  color: #a0a4ab;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.session-type-tag {
  margin-right: 0;
}

.session-actions {
  display: inline-flex;
  gap: 10px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.session-action-icon {
  font-size: 13px;
  color: #8c8c8c;
}

.session-action-icon:hover {
  color: #1677ff;
}

/* 右栏 */
.assistant-main {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.header-scenes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* 消息区 */
.message-area {
  flex: 1 1 auto;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}

.messages,
.welcome-view,
.history-view {
  max-width: 860px;
  margin: 0 auto;
}

/* 空态欢迎 */
.welcome-heading {
  margin-bottom: 24px;
  text-align: center;
}

.welcome-cards {
  margin-top: 8px;
}

.welcome-card-item {
  margin-bottom: 16px;
  text-align: center;
}

.welcome-card-icon {
  font-size: 30px;
  color: #1677ff;
}

.welcome-card-title {
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.welcome-card-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 历史视图 */
.history-card {
  margin-top: 24px;
}

.history-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.history-tip {
  margin: 16px 0;
  font-size: 13px;
  line-height: 1.7;
  color: #8c8c8c;
}

/* 消息气泡 */
.msg-row {
  display: flex;
  margin-bottom: 18px;
}

.msg-user {
  justify-content: flex-end;
}

.bubble-user {
  max-width: 75%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  color: #fff;
  white-space: pre-wrap;
  word-break: break-word;
  background: #1677ff;
  border-radius: 12px;
}

.msg-assistant {
  justify-content: flex-start;
}

.agent-avatar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin-right: 10px;
  font-size: 18px;
  color: #1677ff;
  background: #e6f0ff;
  border-radius: 50%;
}

.bubble-assistant {
  max-width: 80%;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.bubble-agent-tag {
  margin-bottom: 8px;
}

.thinking {
  font-size: 13px;
  color: #8c8c8c;
}

.bubble-alert {
  margin-top: 8px;
}

.bubble-retry {
  margin-top: 8px;
}

/* 输入区 */
.composer {
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.composer-tool {
  margin-bottom: 8px;
}

.composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.composer-row .ant-btn {
  flex: 0 0 auto;
}

/* 简历优化审核操作区 */
.optimize-result {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}

.optimize-score {
  margin-bottom: 6px;
  font-size: 13px;
  color: #1f2937;
}

.optimize-suggestions-title {
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
}

.optimize-suggestions-list {
  margin-bottom: 8px;
}

.optimize-suggestion-item {
  padding: 2px 0 !important;
  font-size: 13px;
  color: #4b5563;
}

.optimize-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

/* 附带简历弹窗 */
.resume-picker {
  width: 100%;
  margin-bottom: 12px;
}

.resume-picker-tip {
  margin-bottom: 12px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 窄屏隐藏左栏 */
@media (max-width: 768px) {
  .assistant-sidebar {
    display: none;
  }
}
</style>
