<script setup lang="ts">
/**
 * 模拟面试进行页
 *
 * 实时问答复用 AI 流式链路（useChatStream）：
 * - 每轮问答持久化到 interview_message：用户回复 messageType=answer，
 *   AI 回复按内容判定 question / evaluation 后落库；
 * - 顶部"结束面试"回填时长、状态并跳转复盘页；
 * - 面试进行中离开页面时给出提示。
 */

import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { message } from 'ant-design-vue'
import { RobotOutlined } from '@ant-design/icons-vue'

import {
  appendInterviewMessage,
  getInterviewDetail,
  updateInterview,
} from '@/api/interviews'
import { getResumeDetail, pageResumes } from '@/api/resumes'
import { useChatStream } from '@/composables/useChatStream'
import MdContent from '@/components/MdContent.vue'
import type {
  InterviewMessage,
  InterviewRecord,
  InterviewType,
  ResumeRecord,
} from '@/types/business'

const route = useRoute()
const router = useRouter()

/** 面试 ID（路由参数；雪花 id 超出 JS 安全整数，须以字符串保留精度） */
const interviewId = route.params.id as string

/** Agent 展示元信息（与 AssistantView.AGENT_META 色值对齐，复用色板） */
const AGENT_META: Record<string, { label: string; color: string }> = {
  job: { label: '岗位匹配顾问', color: 'blue' },
  resume: { label: '简历优化专家', color: 'green' },
  tech: { label: '技术面试官', color: 'orange' },
  hr: { label: 'HR面试官', color: 'purple' },
  chat: { label: 'AI助手', color: 'default' },
}

/** 获取 Agent 元信息，未知值兜底为 chat */
function agentMeta(agent?: string): { label: string; color: string } {
  return AGENT_META[agent ?? 'chat'] ?? AGENT_META.chat
}

/** 面试类型中文名 */
function typeLabel(type?: InterviewType | number): string {
  return type === 2 ? 'HR面' : '技术面'
}

/** 时间戳 → HH:mm:ss */
function fmtTime(value?: string): string {
  if (!value) {
    return ''
  }
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) {
    return ''
  }
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 面试创建时间戳（用于时长计算） */
const createTime = ref<number>(Date.now())

/* --------------------------------- 流式控制器 -------------------------------- */

/** 已持久化到后端的对话消息（含用户与 AI） */
const persisted = ref<InterviewMessage[]>([])

/** 最新简历文本（面试透传给 AI，支撑结合简历个性化提问；无简历为空串） */
const resumeText = ref('')

/** 当前 AI 回复占位（流式生成中） */
const streamingAssistant = ref<{
  content: string
  agent?: string
  loading: boolean
} | null>(null)

/** 输入框文本 */
const inputText = ref('')

const stream = useChatStream({
  onMeta: (data) => {
    if (streamingAssistant.value) {
      streamingAssistant.value.agent = data.agent
    }
  },
  onChunk: (text) => {
    if (streamingAssistant.value) {
      streamingAssistant.value.content += text
    }
    autoScroll()
  },
  onFinal: (full) => {
    if (streamingAssistant.value) {
      streamingAssistant.value.content = full
      streamingAssistant.value.loading = false
    }
    autoScroll()
    // AI 回复完成：按内容判定 question / evaluation 后持久化
    const content = full ?? ''
    // 仅当回复结尾（末句）含问号才判定为 question；
    // 问号出现在前半段、结尾是陈述性总结时判 evaluation，使复盘按类型统计准确。
    // 说明：这是启发式判定（非精确语义识别）；若 AI 以"还有问题可以随时问我"等
    // 陈述句收尾且句中含问号，仍可能被判为 question，属已知局限。
    const tail = content.slice(-60)
    const isQuestion = tail.includes('?') || tail.includes('？')
    void persistAssistant(content, isQuestion ? 'question' : 'evaluation')
    streamingAssistant.value = null
  },
  onError: (msg) => {
    if (streamingAssistant.value) {
      streamingAssistant.value.loading = false
      if (!streamingAssistant.value.content) {
        streamingAssistant.value.content = msg
      }
    }
  },
})

const { isStreaming, send: streamSend, stop: streamStop } = stream

/* --------------------------------- 面试数据 --------------------------------- */

/** 面试详情加载状态 */
const loading = ref(false)
/** 面试详情 */
const interview = ref<InterviewRecord | null>(null)
/** 详情加载失败标记 */
const loadError = ref(false)

/**
 * 加载面试详情（含历史消息）；失败置错误兜底。
 * 已结束的面试直接落到复盘页。
 */
async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    const res = await getInterviewDetail(interviewId)
    interview.value = res.data
    persisted.value = res.data.messages ?? []
    const create = res.data.createTime
    if (create) {
      const d = new Date(create).getTime()
      if (!Number.isNaN(d)) {
        createTime.value = d
      }
    }
    if (res.data.status !== 1) {
      router.replace(`/interviews/${interviewId}/review`)
    }
  } catch (error) {
    console.warn('[interview-session] 面试详情加载失败:', error)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 拉取面试上下文简历：优先取面试关联的简历（getResumeDetail），
 * 未关联时回退到当前用户最新一条；取优化后内容（无则原始内容）。
 * 失败仅告警并置空，不阻断面试流程。
 */
async function loadResumeText(): Promise<void> {
  try {
    const resumeId = interview.value?.resumeId
    let resume: ResumeRecord | null = null
    if (resumeId) {
      const res = await getResumeDetail(resumeId)
      resume = res.data ?? null
    } else {
      const res = await pageResumes({ pageNum: 1, pageSize: 1 })
      resume = res.data?.list?.[0] ?? null
    }
    resumeText.value = resume?.optimizedContent || resume?.originalContent || ''
  } catch (error) {
    console.warn('简历加载失败，面试将不附带简历：', error)
    resumeText.value = ''
  }
}

/* --------------------------------- 消息操作 --------------------------------- */

/**
 * 持久化一条面试消息；失败降级提示但不阻断对话。
 *
 * @param role        user / assistant
 * @param messageType answer / question / evaluation
 * @param content     消息内容
 */
async function persistMessage(
  role: string,
  messageType: string,
  content: string,
): Promise<void> {
  try {
    const res = await appendInterviewMessage(interviewId, {
      role,
      messageType,
      content,
    })
    // 立即将新消息追加到本地消息列表，保证本轮问答即时可见（无需刷新）
    if (res.data) {
      persisted.value.push(res.data)
    }
  } catch (error) {
    console.warn('[interview-session] 消息持久化失败:', error)
    message.warning('消息保存失败，不影响对话')
  }
}

/** 持久化用户回复（answer） */
async function persistUser(content: string): Promise<void> {
  await persistMessage('user', 'answer', content)
}

/** 持久化 AI 回复（question/evaluation） */
async function persistAssistant(content: string, messageType: string): Promise<void> {
  await persistMessage('assistant', messageType, content)
}

/**
 * 发送消息：先持久化用户回复，再发起流式 AI 回答。
 *
 * @param text    指定文本（首问透传），缺省取输入框
 * @param options 选项：skipPersist=true 时不落库用户消息（用于自动启动首问）
 */
async function sendMessage(
  text?: string,
  options?: { skipPersist?: boolean },
): Promise<void> {
  const content = (text ?? inputText.value).trim()
  if (!content || isStreaming.value) {
    return
  }
  inputText.value = ''
  // 自动启动首问（skipPersist）是启动指令而非面试回答，不落 user answer 库
  if (!options?.skipPersist) {
    void persistUser(content)
  }
  streamingAssistant.value = { content: '', agent: undefined, loading: true }
  await nextTick()
  scrollToBottom()
  try {
    await streamSend({
      query: content,
      sessionId: interviewId,
      resumeText: resumeText.value || undefined,
    })
  } finally {
    if (streamingAssistant.value) {
      streamingAssistant.value.loading = false
    }
  }
}

/* --------------------------------- 滚动控制 --------------------------------- */

/** 消息区滚动容器 */
const messageAreaRef = ref<HTMLElement | null>(null)
/** 是否吸附在底部 */
const stickToBottom = ref(true)

/** 消息区滚动事件：更新是否吸附底部 */
function onMessageScroll(): void {
  const el = messageAreaRef.value
  if (!el) {
    return
  }
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 120
}

/** 强制滚动到底部 */
function scrollToBottom(): void {
  const el = messageAreaRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

/** 流式增量时仅吸附状态自动滚动 */
function autoScroll(): void {
  if (stickToBottom.value) {
    void nextTick(() => scrollToBottom())
  }
}

/* --------------------------------- 输入区 --------------------------------- */

/**
 * 输入框按键：Enter（非 Shift、非中文组词中）发送。
 *
 * @param event 键盘事件
 */
function onInputKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void sendMessage()
  }
}

/** 停止生成 */
function stopGenerate(): void {
  streamStop()
  if (streamingAssistant.value) {
    streamingAssistant.value.loading = false
  }
}

/* --------------------------------- 结束面试 --------------------------------- */

/** 结束提交中 */
const finishing = ref(false)

/**
 * 结束面试：回填时长与状态，成功后跳转复盘页。
 */
async function handleFinish(): Promise<void> {
  if (!interview.value) {
    return
  }
  finishing.value = true
  try {
    const durationSeconds = Math.max(
      0,
      Math.floor((Date.now() - createTime.value) / 1000),
    )
    await updateInterview(interviewId, {
      status: 2,
      durationSeconds,
    })
    message.success('面试已结束')
    router.push(`/interviews/${interviewId}/review`)
  } catch (error) {
    console.warn('[interview-session] 结束面试失败:', error)
  } finally {
    finishing.value = false
  }
}

/* --------------------------------- 离开提示 --------------------------------- */

/** 面试进行中离开时提示（组件守卫，离开时提示可继续进入） */

/** 是否进行中（需离开提示） */
const isOngoing = computed(() => interview.value?.status === 1)

onBeforeRouteLeave(() => {
  // 正常"结束面试"跳转复盘时不提示；仅非结束态的离开（切页/刷新）提醒
  if (isOngoing.value && !finishing.value) {
    message.warning('面试进行中，离开后仍可在记录列表继续进入')
  }
})

onMounted(async () => {
  // 先加载历史与简历，再决定是否自动发首问，消除"加载/发送"竞态
  await loadDetail()
  await loadResumeText()
  const first = (route.query.first as string) ?? ''
  // 仅当该面试无任何历史消息（全新面试）时才自动发首问；
  // 续面 / 刷新（persisted 非空）不再重复发启动指令。
  // 自动首问是启动指令，skipPersist 使其不落 user answer 库。
  if (first && persisted.value.length === 0) {
    await sendMessage(first, { skipPersist: true })
  }
})

onUnmounted(() => {
  streamStop()
})
</script>

<template>
  <div class="interview-session">
    <!-- 顶栏：标题 + 结束面试 -->
    <a-card :bordered="false" class="session-head">
      <div class="head-bar">
        <div class="head-info">
          <a-tag :color="interview?.interviewType === 2 ? 'purple' : 'orange'">
            {{ typeLabel(interview?.interviewType) }}
          </a-tag>
          <span class="head-title">
            {{ interview?.targetPosition || '模拟面试' }}
          </span>
          <span v-if="interview?.targetCompany" class="head-company">
            · {{ interview.targetCompany }}
          </span>
        </div>
        <a-popconfirm
          title="确认结束本轮面试？结束后将进入复盘页"
          ok-text="结束"
          cancel-text="取消"
          @confirm="handleFinish"
        >
          <a-button danger :loading="finishing">结束面试</a-button>
        </a-popconfirm>
      </div>
    </a-card>

    <!-- 消息区 -->
    <a-card :bordered="false" class="message-card" :loading="loading">
      <a-result
        v-if="loadError"
        status="warning"
        title="面试加载失败"
        sub-title="请确认面试记录存在且属于当前账号"
      />

      <template v-else>
        <div
          ref="messageAreaRef"
          class="message-area"
          @scroll="onMessageScroll"
        >
          <template v-for="msg in persisted" :key="msg.id">
            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'" class="msg-row msg-user">
              <div class="bubble-user">{{ msg.content }}</div>
              <span class="msg-time">{{ fmtTime(msg.createTime) }}</span>
            </div>
            <!-- AI 消息 -->
            <div v-else class="msg-row msg-assistant">
              <div class="agent-avatar">
                <RobotOutlined />
              </div>
              <div class="bubble-assistant">
                <a-tag
                  v-if="msg.messageType === 'question'"
                  color="blue"
                  class="msg-type-tag"
                >
                  提问
                </a-tag>
                <a-tag
                  v-else-if="msg.messageType === 'evaluation'"
                  color="green"
                  class="msg-type-tag"
                >
                  点评
                </a-tag>
                <MdContent :content="msg.content" />
                <span class="msg-time">{{ fmtTime(msg.createTime) }}</span>
              </div>
            </div>
          </template>

          <!-- 流式中的 AI 占位 -->
          <div v-if="streamingAssistant" class="msg-row msg-assistant">
            <div class="agent-avatar">
              <RobotOutlined />
            </div>
            <div class="bubble-assistant">
              <a-tag
                v-if="streamingAssistant.agent"
                :color="agentMeta(streamingAssistant.agent).color"
                class="msg-type-tag"
              >
                {{ agentMeta(streamingAssistant.agent).label }}
              </a-tag>
              <div
                v-if="streamingAssistant.loading && !streamingAssistant.content"
                class="thinking"
              >
                正在思考...
              </div>
              <MdContent
                v-if="streamingAssistant.content"
                :content="streamingAssistant.content"
                :loading="streamingAssistant.loading"
              />
            </div>
          </div>

          <a-empty
            v-if="persisted.length === 0 && !streamingAssistant"
            description="输入您的第一句回答，面试官将针对岗位展开提问"
          />
        </div>

        <!-- 输入区 -->
        <footer class="composer">
          <div class="composer-row">
            <a-textarea
              v-model:value="inputText"
              :auto-size="{ minRows: 1, maxRows: 4 }"
              placeholder="输入回答，Enter 发送，Shift+Enter 换行"
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
      </template>
    </a-card>
  </div>
</template>

<style scoped>
.interview-session {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 190px);
  min-height: 480px;
}

.session-head:deep(.ant-card-body) {
  padding: 12px 16px;
}

.head-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.head-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.head-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.head-company {
  font-size: 13px;
  color: #8c8c8c;
}

.message-card {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-card:deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}

.message-area {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 4px 8px 12px;
}

.msg-row {
  display: flex;
  margin-bottom: 16px;
}

.msg-user {
  justify-content: flex-end;
  align-items: flex-end;
  flex-direction: column;
}

.bubble-user {
  max-width: 70%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
  color: #fff;
  background: #1677ff;
  border-radius: 8px 8px 2px 8px;
  word-break: break-word;
  white-space: pre-wrap;
}

.msg-assistant {
  align-items: flex-start;
}

.agent-avatar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-right: 10px;
  color: #1677ff;
  background: #eef4ff;
  border-radius: 50%;
}

.bubble-assistant {
  max-width: 75%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px 8px 8px 2px;
  word-break: break-word;
}

.msg-type-tag {
  margin-right: 8px;
}

.msg-time {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #bfbfbf;
}

.thinking {
  font-size: 13px;
  color: #8c8c8c;
}

.composer {
  flex: 0 0 auto;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.composer-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.composer-row .ant-textarea {
  flex: 1 1 auto;
}
</style>