<script setup lang="ts">
/**
 * 工作台首页
 *
 * 聚合展示：欢迎信息与日期、岗位市场概览（统计）、AI 求职助手快捷入口、
 * 我的能力概览。各卡片数据独立加载、独立 try/catch 降级，单接口失败
 * 不影响其他卡片，接口异常时以空态兜底，避免整页白屏。
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import {
  CalendarOutlined,
  CodeOutlined,
  FileTextOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'
import type { Component } from 'vue'

import { getJobStats } from '@/api/jobs'
import { getMyAbility } from '@/api/ability'
import type { AbilityProfile, JobStats, NameCount } from '@/types/business'
import { ABILITY_DIMENSIONS } from '@/types/business'
import { useUserStore } from '@/store/modules/user'

// dayjs 使用中文 locale，dddd 输出“星期一”等中文星期
dayjs.locale('zh-cn')

const router = useRouter()
const userStore = useUserStore()

/** 当前日期（YYYY年MM月DD日 + 中文星期） */
const today = dayjs().format('YYYY年MM月DD日 dddd')

/** 欢迎语中的用户称呼：昵称 > 用户名 > 同学 */
const nickname = computed<string>(
  () => userStore.userInfo?.nickname || userStore.userInfo?.username || '同学',
)

/* ------------------------------ 岗位市场概览 ------------------------------ */

/** 岗位统计加载状态 */
const statsLoading = ref(false)
/** 岗位统计数据（null 表示尚未加载成功） */
const jobStats = ref<JobStats | null>(null)

/** 岗位类别分布（按数量降序） */
const categoryCounts = computed<NameCount[]>(() =>
  [...(jobStats.value?.categoryCounts ?? [])]
    .map((item) => ({ name: item.name || '未分类', count: item.count }))
    .sort((a, b) => b.count - a.count),
)

/** 热门城市 Top10（后端已限量，前端再兜底截断） */
const cityTop = computed<NameCount[]>(() =>
  [...(jobStats.value?.cityCounts ?? [])]
    .map((item) => ({ name: item.name || '未分类', count: item.count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10),
)

/**
 * 加载岗位市场统计；失败置空，由卡片空态兜底
 */
async function loadStats(): Promise<void> {
  statsLoading.value = true
  try {
    const res = await getJobStats()
    jobStats.value = res.data
  } catch (error) {
    console.warn('[dashboard] 岗位统计加载失败:', error)
    jobStats.value = null
  } finally {
    statsLoading.value = false
  }
}

/* ----------------------------- AI 求职助手入口 ----------------------------- */

/** 快捷入口项类型 */
interface AssistantEntry {
  /** 场景标识，对应 assistant 页 query.scene */
  scene: string
  /** 入口标题 */
  title: string
  /** 一句话说明 */
  desc: string
  /** 图标组件 */
  icon: Component
  /** 主题色（蓝青系） */
  color: string
}

/** AI 求职助手四个快捷入口 */
const assistantEntries: AssistantEntry[] = [
  {
    scene: 'job',
    title: '岗位匹配',
    desc: '结合意向与技能，智能推荐在招岗位',
    icon: RobotOutlined,
    color: '#1677ff',
  },
  {
    scene: 'resume',
    title: '简历优化',
    desc: 'STAR 法则诊断改写，对齐目标 JD',
    icon: FileTextOutlined,
    color: '#0958d9',
  },
  {
    scene: 'tech',
    title: '技术面试',
    desc: '模拟技术面与考点追问，实时点评',
    icon: CodeOutlined,
    color: '#13c2c2',
  },
  {
    scene: 'hr',
    title: 'HR 面试',
    desc: '行为面试与职业规划模拟演练',
    icon: TeamOutlined,
    color: '#2f54eb',
  },
]

/**
 * 跳转到 AI 助手场景页（/assistant 下一批上线，当前由兜底路由处理）
 *
 * @param scene 场景标识 job/resume/tech/hr
 */
function goAssistant(scene: string): void {
  router.push({ path: '/assistant', query: { scene } })
}

/* ------------------------------- 我的能力概览 ------------------------------ */

/** 能力画像加载状态 */
const abilityLoading = ref(false)
/** 各维度最新能力快照 */
const abilityList = ref<AbilityProfile[]>([])

/** 能力行（维度 + 得分），按标准五维度顺序排列 */
const abilityRows = computed<{ dimension: string; score: number }[]>(() => {
  const list = abilityList.value
  const rows: { dimension: string; score: number }[] = []

  // 标准五维度优先，按 ABILITY_DIMENSIONS 固定顺序
  ABILITY_DIMENSIONS.forEach((dimension) => {
    const hit = list.find((item) => item.dimension === dimension)
    if (hit) {
      rows.push({ dimension, score: hit.dimensionScore })
    }
  })
  // 后端返回但不在标准维度内的项追加在末尾
  list.forEach((item) => {
    if (!rows.some((row) => row.dimension === item.dimension)) {
      rows.push({ dimension: String(item.dimension), score: item.dimensionScore })
    }
  })
  return rows
})

/** 是否无能力数据（用于空态） */
const abilityEmpty = computed<boolean>(() => abilityRows.value.length === 0)

/**
 * 加载我的能力画像；失败静默降级为空态，不干扰其他卡片
 */
async function loadAbility(): Promise<void> {
  abilityLoading.value = true
  try {
    const res = await getMyAbility()
    abilityList.value = res.data ?? []
  } catch (error) {
    // 能力画像为增强信息，失败仅告警并展示空态
    console.warn('[dashboard] 能力画像加载失败:', error)
    abilityList.value = []
  } finally {
    abilityLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadAbility()
})
</script>

<template>
  <div class="dashboard">
    <!-- 欢迎卡片 -->
    <a-card :bordered="false" class="welcome-card">
      <div class="welcome-inner">
        <div class="welcome-left">
          <div class="welcome-title">
            你好，{{ nickname }}，今天也要积极准备校招
          </div>
          <div class="welcome-sub">愿你拿到心仪的 offer，冲鸭！</div>
        </div>
        <div class="welcome-date">
          <CalendarOutlined class="welcome-date-icon" />
          <span>{{ today }}</span>
        </div>
      </div>
    </a-card>

    <!-- 岗位市场概览 -->
    <a-card
      :bordered="false"
      :loading="statsLoading"
      title="岗位市场概览"
      class="panel-card"
    >
      <a-empty
        v-if="!jobStats"
        description="岗位统计暂不可用"
      />
      <template v-else>
        <!-- 顶部统计数字 -->
        <a-row :gutter="16">
          <a-col :xs="24" :sm="8">
            <div class="stat-box">
              <a-statistic title="在招岗位总数" :value="jobStats.totalCount" suffix="个" />
            </div>
          </a-col>
          <a-col :xs="24" :sm="8">
            <div class="stat-box">
              <a-statistic title="覆盖岗位类别" :value="categoryCounts.length" suffix="类" />
            </div>
          </a-col>
          <a-col :xs="24" :sm="8">
            <div class="stat-box">
              <a-statistic title="覆盖招聘城市" :value="cityTop.length" suffix="城" />
            </div>
          </a-col>
        </a-row>

        <!-- 类别分布 + 热门城市 -->
        <a-row :gutter="24" class="stats-detail">
          <a-col :xs="24" :md="14">
            <div class="sub-title">岗位类别分布</div>
            <div v-if="categoryCounts.length" class="tag-cloud">
              <a-tag
                v-for="item in categoryCounts"
                :key="item.name"
                color="blue"
                class="cat-tag"
              >
                {{ item.name }} · {{ item.count }}
              </a-tag>
            </div>
            <a-empty v-else description="暂无类别数据" />
          </a-col>
          <a-col :xs="24" :md="10">
            <div class="sub-title">热门城市 Top10</div>
            <a-list
              v-if="cityTop.length"
              size="small"
              :data-source="cityTop"
              :split="true"
            >
              <template #renderItem="{ item, index }">
                <a-list-item>
                  <span class="city-name">
                    <span class="city-rank">{{ index + 1 }}</span>
                    {{ item.name }}
                  </span>
                  <a-tag color="geekblue">{{ item.count }} 个</a-tag>
                </a-list-item>
              </template>
            </a-list>
            <a-empty v-else description="暂无城市数据" />
          </a-col>
        </a-row>
      </template>
    </a-card>

    <!-- AI 求职助手快捷入口 -->
    <a-card :bordered="false" title="AI 求职助手" class="panel-card">
      <a-row :gutter="16">
        <a-col
          v-for="entry in assistantEntries"
          :key="entry.scene"
          :xs="24"
          :sm="12"
          :lg="6"
        >
          <a-card
            hoverable
            :bordered="true"
            class="assist-card"
            @click="goAssistant(entry.scene)"
          >
            <div class="assist-inner">
              <div
                class="assist-icon"
                :style="{ backgroundColor: `${entry.color}1a`, color: entry.color }"
              >
                <component :is="entry.icon" />
              </div>
              <div class="assist-text">
                <div class="assist-title">{{ entry.title }}</div>
                <div class="assist-desc">{{ entry.desc }}</div>
              </div>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- 我的能力概览 -->
    <a-card
      :bordered="false"
      :loading="abilityLoading"
      title="我的能力概览"
      class="panel-card"
    >
      <template v-if="!abilityEmpty">
        <div v-for="row in abilityRows" :key="row.dimension" class="ability-row">
          <div class="ability-name">{{ row.dimension }}</div>
          <a-progress
            class="ability-bar"
            size="small"
            :percent="row.score"
            :stroke-color="'#1677ff'"
          />
          <div class="ability-score">{{ row.score }}</div>
        </div>
        <div class="ability-footer">
          <router-link to="/ability" class="ability-link">查看完整画像</router-link>
        </div>
      </template>
      <a-empty v-else description="完善求职画像后，AI 将在模拟面试中为你生成能力评估" />
    </a-card>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 欢迎卡片 */
.welcome-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.welcome-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.welcome-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #8c8c8c;
}

.welcome-date {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #595959;
}

.welcome-date-icon {
  color: #1677ff;
  font-size: 18px;
}

/* 统计数字块 */
.stat-box {
  padding: 16px 20px;
  background: #f7faff;
  border: 1px solid #eef3ff;
  border-radius: 8px;
}

.stats-detail {
  margin-top: 20px;
}

.sub-title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

/* 类别标签云 */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cat-tag {
  margin-right: 0;
  padding: 2px 4px;
}

/* 城市列表 */
.city-name {
  display: inline-flex;
  align-items: center;
  color: #1f2937;
}

.city-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-right: 8px;
  font-size: 12px;
  color: #1677ff;
  background: #eef4ff;
  border-radius: 50%;
}

/* AI 快捷入口卡片 */
.assist-card {
  margin-bottom: 16px;
}

.assist-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assist-icon {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  font-size: 22px;
  border-radius: 10px;
}

.assist-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.assist-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #8c8c8c;
}

/* 能力概览 */
.ability-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.ability-name {
  flex: 0 0 96px;
  font-size: 13px;
  color: #1f2937;
}

.ability-bar {
  flex: 1 1 auto;
  margin-bottom: 0;
}

.ability-score {
  flex: 0 0 32px;
  font-size: 13px;
  font-weight: 600;
  color: #1677ff;
  text-align: right;
}

.ability-footer {
  margin-top: 4px;
  text-align: right;
}

.ability-link {
  font-size: 13px;
  color: #1677ff;
  text-decoration: none;
}

.ability-link:hover {
  text-decoration: underline;
}
</style>
