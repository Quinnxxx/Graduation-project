<script setup lang="ts">
/**
 * 模拟面试复盘页
 *
 * 展示面试详情摘要与 AI 生成的复盘报告：
 * - getInterviewDetail(id) 渲染描述区，时长秒转 mm:ss；
 * - 复盘报告存在时用 MdContent 渲染 Markdown；
 * - "生成复盘报告"按钮调 /ai/chat（非流式）基于对话生成结构化报告，
 *   正则提取"总体评分"，回填 overallScore/evaluationReport/status 后刷新；
 *   评分未命中时仅回填报告与状态，保留原评分并在页面提示人工核对；
 * - 报告返回后解析末尾五维能力评分 JSON，分次写入能力画像
 *   （saveAbility，最多 5 次，单条失败由 request.ts 统一提示，不阻断报告保存）。
 */

import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'

import { chat } from '@/api/ai'
import { getInterviewDetail, updateInterview } from '@/api/interviews'
import { saveAbility } from '@/api/ability'
import MdContent from '@/components/MdContent.vue'
import type { AbilityDimension, InterviewRecord, InterviewType } from '@/types/business'
import { ABILITY_DIMENSIONS } from '@/types/business'

const route = useRoute()

/** 面试 ID（路由参数；雪花 id 超出 JS 安全整数，须以字符串保留精度） */
const interviewId = route.params.id as string

/** 面试详情加载状态 */
const loading = ref(false)
/** 面试详情 */
const interview = ref<InterviewRecord | null>(null)
/** 详情加载失败标记 */
const loadError = ref(false)
/** 报告生成中 */
const generating = ref(false)
/** 评分未从报告解析出的提示标记 */
const manualScore = ref(false)

/** 面试类型中文名 */
function typeLabel(type?: InterviewType | number): string {
  return type === 2 ? 'HR面' : '技术面'
}

/** 难度标签元信息 */
const DIFF_META: Record<number, string> = {
  1: '简单',
  2: '中等',
  3: '困难',
}

/** 状态标签元信息 */
const STATUS_META: Record<number, { label: string; color: string }> = {
  1: { label: '进行中', color: 'processing' },
  2: { label: '已完成', color: 'green' },
  3: { label: '已中断', color: 'red' },
}

/** 空值兜底为 “-” */
function dash(value: unknown): string {
  return value === null || value === undefined || value === '' ? '-' : String(value)
}

/**
 * 时长秒转 mm:ss；空值兜底 "-"。
 *
 * @param seconds 秒数
 * @returns mm:ss 或 "-"
 */
function fmtDuration(seconds?: number): string {
  if (seconds === null || seconds === undefined || seconds < 0) {
    return '-'
  }
  const mm = Math.floor(seconds / 60)
  const ss = Math.floor(seconds % 60)
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

/**
 * 加载面试详情。
 */
async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    const res = await getInterviewDetail(interviewId)
    interview.value = res.data
  } catch (error) {
    console.warn('[interview-review] 复盘加载失败:', error)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 从生成的报告中提取总体评分（"总体评分[:：]?\s*(\d+)"）；未命中返回 null。
 *
 * @param report AI 生成的复盘报告文本
 * @returns 0-100 评分或 null
 */
function parseOverallScore(report: string): number | null {
  const match = report.match(/总体评分[:：]?\s*(\d{1,3})/)
  if (!match) {
    return null
  }
  const score = Number(match[1])
  return score >= 0 && score <= 100 ? score : null
}

/** 复盘报告五维评分映射（键为能力维度，值为 0-100 得分） */
type AbilityScoreMap = Partial<Record<AbilityDimension, number>>

/**
 * 提取复盘报告末尾要求的五维评分 JSON 文本。
 *
 * 优先匹配 ```json 代码块；再以维度键 "专业基础" 为锚点向前定位对象起点
 * （正文可能包含其它花括号，锚定比取首个 '{' 更稳）；最后回退取首个
 * 顶层 JSON 对象。括号匹配区分字符串内花括号。
 *
 * @param report AI 生成的复盘报告文本
 * @returns JSON 对象文本；无法提取时返回 null
 */
function extractAbilityJson(report: string): string | null {
  const fence = report.match(/```json\s*\n?([\s\S]*?)\n?\s*```/)
  const text = fence ? fence[1] : report
  // 优先以维度键定位对象起点
  const anchor = text.indexOf('"专业基础"')
  if (anchor >= 0) {
    const start = text.lastIndexOf('{', anchor)
    if (start >= 0) {
      const obj = extractBalancedObject(text, start)
      if (obj) {
        return obj
      }
    }
  }
  // 回退：首个 '{' 到对应 '}' 的顶层对象
  const start = text.indexOf('{')
  if (start < 0) {
    return null
  }
  return extractBalancedObject(text, start)
}

/**
 * 从文本 start 位置（'{'）开始做括号匹配，返回到对应 '}' 的完整对象文本。
 *
 * 遍历时区分字符串内花括号（"{" / "\\" / '"'），不会被键值文本干扰。
 *
 * @param text 目标文本
 * @param start '{' 起始下标
 * @returns 平衡后的对象文本；无法配平返回 null
 */
function extractBalancedObject(text: string, start: number): string | null {
  let depth = 0
  let inStr = false
  let escaped = false
  for (let i = start; i < text.length; i += 1) {
    const ch = text[i]
    if (inStr) {
      if (escaped) {
        escaped = false
      } else if (ch === '\\') {
        escaped = true
      } else if (ch === '"') {
        inStr = false
      }
    } else if (ch === '"') {
      inStr = true
    } else if (ch === '{') {
      depth += 1
    } else if (ch === '}') {
      depth -= 1
      if (depth === 0) {
        return text.slice(start, i + 1)
      }
    }
  }
  return null
}

/**
 * 从复盘报告中解析五维能力评分（仅保留 ABILITY_DIMENSIONS 中 0-100 的整数得分）。
 *
 * 解析失败 / 维度缺失时该维度不出现在结果中，由调用方跳过对应写入。
 *
 * @param report AI 生成的复盘报告文本
 * @returns 五维评分映射（缺失维度不出现）
 */
function parseAbilityScores(report: string): AbilityScoreMap {
  const jsonText = extractAbilityJson(report)
  if (!jsonText) {
    return {}
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(jsonText)
  } catch {
    return {}
  }
  const record = parsed as Record<string, unknown>
  const scores: AbilityScoreMap = {}
  for (const dim of ABILITY_DIMENSIONS) {
    const raw = Number(record[dim])
    if (Number.isFinite(raw) && raw >= 0 && raw <= 100) {
      scores[dim] = Math.round(raw)
    }
  }
  return scores
}

/**
 * 将报告解析出的五维评分分次写入能力画像（单维度接口，最多 5 次）。
 *
 * 不阻断报告主流程：单条写入失败由 request.ts 统一拦截提示，本函数仅
 * console 记录失败数；报告保存与页面刷新不受影响。
 *
 * @param report AI 生成的复盘报告文本
 */
async function syncAbilityScores(report: string): Promise<void> {
  const scores = parseAbilityScores(report)
  const dims = ABILITY_DIMENSIONS.filter((dim) => scores[dim] !== undefined)
  if (dims.length === 0) {
    return
  }
  const results = await Promise.allSettled(
    dims.map((dim) =>
      saveAbility({ dimension: dim, dimensionScore: scores[dim] as number }),
    ),
  )
  const failed = results.filter((r) => r.status === 'rejected').length
  if (failed > 0) {
    console.warn(`[interview-review] 能力画像写入失败 ${failed}/${dims.length} 个维度`)
  }
}

/**
 * 生成复盘报告：调 AI 非流式接口，解析评分后回填、同步能力画像并刷新。
 */
async function handleGenerateReport(): Promise<void> {
  const current = interview.value
  if (!current || generating.value) {
    return
  }

  const messages = (current.messages ?? [])
    .map((msg) =>
      msg.role === 'user' ? `面试者：${msg.content}` : `面试官：${msg.content}`,
    )
    .join('\n')

  generating.value = true
  manualScore.value = false
  try {
    const res = await chat({
      query:
        '请基于以下面试对话生成结构化复盘报告（含各能力维度 0-100 评分与总体评分）：\n' +
        (messages || '（暂无对话记录）') +
        '\n\n报告结尾必须独立输出五维能力评分，格式如下（严格遵守，单独代码块）：\n' +
        '```json\n' +
        '{"专业基础":72,"工程实践":78,"算法与数据结构":68,"框架与中间件":75,"软素养":70}\n' +
        '```',
    })

    const aiResult = res.data
    if (aiResult?.error || !aiResult?.finalResponse) {
      message.warning('AI 服务暂不可用')
      return
    }

    const report = aiResult.finalResponse
    const score = parseOverallScore(report)
    const params: { evaluationReport?: string; overallScore?: number; status: number } = {
      evaluationReport: report,
      status: 2,
    }
    if (score !== null) {
      params.overallScore = score
    } else {
      manualScore.value = true
    }

    await updateInterview(interviewId, params)
    await syncAbilityScores(report)
    message.success('复盘报告已生成')
    await loadDetail()
  } catch (error) {
    console.warn('[interview-review] 复盘报告生成失败:', error)
    message.warning('AI 服务暂不可用')
  } finally {
    generating.value = false
  }
}

onMounted(() => {
  void loadDetail()
})
</script>

<template>
  <div class="interview-review">
    <a-card :bordered="false" :loading="loading">
      <a-result
        v-if="loadError"
        status="warning"
        title="复盘加载失败"
        sub-title="请确认面试记录存在且属于当前账号"
      />

      <template v-else-if="interview">
        <a-descriptions bordered size="small" :column="2">
          <a-descriptions-item label="面试类型">
            <a-tag :color="interview.interviewType === 2 ? 'purple' : 'orange'">
              {{ typeLabel(interview.interviewType) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="目标岗位">
            {{ dash(interview.targetPosition) }}
          </a-descriptions-item>
          <a-descriptions-item label="目标公司">
            {{ dash(interview.targetCompany) }}
          </a-descriptions-item>
          <a-descriptions-item label="难度">
            {{ DIFF_META[interview.difficultyLevel ?? 2] ?? '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="面试时长">
            {{ fmtDuration(interview.durationSeconds) }}
          </a-descriptions-item>
          <a-descriptions-item label="提问数">
            {{ interview.questionCount ?? 0 }}
          </a-descriptions-item>
          <a-descriptions-item label="综合评分">
            {{ interview.overallScore ?? '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="STATUS_META[interview.status ?? 2]?.color ?? 'default'">
              {{ STATUS_META[interview.status ?? 2]?.label ?? '-' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">
            {{ dash(interview.createTime) }}
          </a-descriptions-item>
        </a-descriptions>

        <div class="report-head">
          <a-divider orientation="left">AI 复盘报告</a-divider>
          <a-button type="primary" :loading="generating" @click="handleGenerateReport">
            生成复盘报告
          </a-button>
        </div>

        <a-alert
          v-if="manualScore"
          type="warning"
          show-icon
          message="评分未能从报告中自动解析，请在报告中人工核对总体评分"
          class="manual-score-alert"
        />

        <div v-if="interview.evaluationReport" class="report-body">
          <MdContent :content="interview.evaluationReport" />
        </div>
        <a-empty v-else description="AI 复盘报告生成中" class="report-empty" />
      </template>
    </a-card>
  </div>
</template>

<style scoped>
.interview-review {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 20px;
}

.report-head .ant-divider {
  flex: 1;
  min-width: 0;
  margin-top: 0;
  margin-bottom: 0;
}

.manual-score-alert {
  margin-top: 12px;
}

.report-body {
  margin-top: 8px;
  overflow: hidden;
}

.report-empty {
  padding: 48px 0;
}
</style>