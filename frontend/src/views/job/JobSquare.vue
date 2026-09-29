<script setup lang="ts">
/**
 * 岗位广场
 *
 * 校招在招岗位的检索与浏览页：顶部多条件筛选（关键词 / 类别 / 城市 /
 * 学历 / 薪资区间），中部岗位卡片列表 + 分页，点击卡片打开详情抽屉。
 *
 * 数据与容错约定：
 * - 默认只查询在招岗位（status=1）；
 * - 列表加载中使用卡片骨架，请求失败展示 a-result + 重试，不允许白屏；
 * - 详情抽屉打开时按 id 拉取完整信息，字段缺失统一以 “-” 兜底。
 */

import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'

import { getJobDetail, pageJobs } from '@/api/jobs'
import type { JobPosition, JobPositionQuery } from '@/types/business'

const router = useRouter()

/** 岗位类别下拉选项（取自演示数据实际出现的类别，按数量降序） */
const JOB_CATEGORY_OPTIONS = [
  { label: '后端开发', value: '后端开发' },
  { label: 'AI算法', value: 'AI算法' },
  { label: '嵌入式开发', value: '嵌入式开发' },
  { label: '前端开发', value: '前端开发' },
  { label: '测试开发', value: '测试开发' },
  { label: '数据分析', value: '数据分析' },
  { label: '安全开发', value: '安全开发' },
  { label: '实施顾问', value: '实施顾问' },
]

/** 工作城市下拉选项 */
const WORK_CITY_OPTIONS = [
  { label: '北京', value: '北京' },
  { label: '上海', value: '上海' },
  { label: '广州', value: '广州' },
  { label: '深圳', value: '深圳' },
  { label: '杭州', value: '杭州' },
  { label: '南京', value: '南京' },
]

/** 学历要求下拉选项：0 不限 / 1 本科 / 2 硕士 / 3 博士 */
const EDUCATION_OPTIONS = [
  { label: '不限', value: 0 },
  { label: '本科', value: 1 },
  { label: '硕士', value: 2 },
  { label: '博士', value: 3 },
]

/** 筛选表单（输入态，点击查询后才生效） */
const form = reactive({
  /** 关键词 */
  keyword: '',
  /** 岗位类别 */
  jobCategory: undefined as string | undefined,
  /** 工作城市 */
  workCity: undefined as string | undefined,
  /** 学历要求（0 不限 / 1 本科 / 2 硕士 / 3 博士） */
  educationRequirement: undefined as number | undefined,
  /** 最低月薪 K */
  salaryMin: null as number | null,
  /** 最高月薪 K */
  salaryMax: null as number | null,
})

/** 当前页码 */
const pageNum = ref(1)
/** 每页条数 */
const pageSize = ref(10)
/** 总记录数 */
const total = ref(0)
/** 当前页岗位列表 */
const jobList = ref<JobPosition[]>([])
/** 列表加载状态 */
const loading = ref(false)
/** 列表加载失败标记（用于 a-result 兜底） */
const loadError = ref(false)
/** 列表区锚点（分页切换后滚动回列表顶部） */
const listTopRef = ref<HTMLElement | null>(null)

/**
 * 组装分页查询参数；空字符串 / null 统一转为 undefined，
 * status 固定为 1（在招）。
 *
 * @returns 后端岗位分页查询参数
 */
function buildParams(): JobPositionQuery {
  return {
    pageNum: pageNum.value,
    pageSize: pageSize.value,
    status: 1,
    keyword: form.keyword?.trim() || undefined,
    jobCategory: form.jobCategory,
    workCity: form.workCity,
    educationRequirement: form.educationRequirement,
    salaryMin: form.salaryMin ?? undefined,
    salaryMax: form.salaryMax ?? undefined,
  }
}

/**
 * 加载岗位分页数据；失败置 loadError，由页面内 a-result 兜底。
 */
async function loadJobs(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const res = await pageJobs(buildParams())
    jobList.value = res.data?.list ?? []
    total.value = res.data?.total ?? 0
  } catch (error) {
    console.warn('[job-square] 岗位列表加载失败:', error)
    jobList.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 点击查询：筛选条件生效并回到第一页。
 */
function handleSearch(): void {
  pageNum.value = 1
  loadJobs()
}

/**
 * 重置筛选条件并重新加载第一页。
 */
function handleReset(): void {
  form.keyword = ''
  form.jobCategory = undefined
  form.workCity = undefined
  form.educationRequirement = undefined
  form.salaryMin = null
  form.salaryMax = null
  pageNum.value = 1
  loadJobs()
}

/**
 * 分页 / 每页条数变化；切换 pageSize 时强制回到第一页，
 * 并平滑滚动到列表顶部。
 *
 * @param page 目标页码
 * @param size 目标每页条数
 */
async function handlePageChange(page: number, size: number): Promise<void> {
  const sizeChanged = size !== pageSize.value
  pageSize.value = size
  pageNum.value = sizeChanged ? 1 : page
  await loadJobs()
  await nextTick()
  listTopRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/**
 * 分页总数文案
 *
 * @param t 总记录数
 * @returns 文案
 */
function showTotal(t: number): string {
  return `共 ${t} 条`
}

/* --------------------------------- 详情抽屉 -------------------------------- */

/** 抽屉显隐 */
const drawerOpen = ref(false)
/** 详情加载状态 */
const detailLoading = ref(false)
/** 详情加载失败标记 */
const detailError = ref(false)
/** 当前查看的岗位详情 */
const detail = ref<JobPosition | null>(null)

/**
 * 打开岗位详情抽屉并按 id 拉取完整信息。
 *
 * @param id 岗位 ID（雪花 ID 以字符串承载）
 */
async function openDetail(id: number | string): Promise<void> {
  drawerOpen.value = true
  detail.value = null
  detailError.value = false
  detailLoading.value = true
  try {
    const res = await getJobDetail(id)
    detail.value = res.data
  } catch (error) {
    console.warn('[job-square] 岗位详情加载失败:', error)
    detailError.value = true
  } finally {
    detailLoading.value = false
  }
}

/**
 * 跳转 AI 助手进行岗位分析（携带场景与岗位名关键词）。
 */
function analyzeByAi(): void {
  if (!detail.value) {
    return
  }
  router.push({
    path: '/assistant',
    query: { scene: 'job', keyword: detail.value.positionName },
  })
}

/**
 * 空值兜底为 “-”。
 *
 * @param value 任意字段值
 * @returns 可展示文本
 */
function dash(value: unknown): string {
  return value === null || value === undefined || value === '' ? '-' : String(value)
}

/**
 * 日期格式化为 YYYY-MM-DD；无法解析时回退原文本。
 *
 * @param value 日期字符串
 * @returns 格式化后的日期
 */
function fmtDate(value?: string): string {
  if (!value) {
    return '-'
  }
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD') : String(value)
}

/**
 * 拼接薪资区间文本。
 *
 * @param job 岗位信息
 * @returns 如 25-45K
 */
function salaryRange(job: JobPosition): string {
  const { salaryMin, salaryMax } = job
  if (salaryMin != null && salaryMax != null) {
    return `${salaryMin}-${salaryMax}K`
  }
  if (salaryMin != null) {
    return `${salaryMin}K 起`
  }
  if (salaryMax != null) {
    return `${salaryMax}K 以内`
  }
  return '-'
}

/**
 * 卡片薪资展示：优先薪资原文（如 25-45K·16薪），缺失时回退区间。
 *
 * @param job 岗位信息
 * @returns 薪资展示文本
 */
function salaryText(job: JobPosition): string {
  return job.salaryNote || salaryRange(job)
}

onMounted(() => {
  loadJobs()
})
</script>

<template>
  <div class="job-square">
    <!-- 筛选区 -->
    <a-card :bordered="false" class="filter-card">
      <a-row :gutter="[16, 16]">
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-input-search
            v-model:value="form.keyword"
            placeholder="搜索岗位名称 / 公司 / JD"
            allow-clear
            enter-button
            @search="handleSearch"
            @clear="handleSearch"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-select
            v-model:value="form.jobCategory"
            :options="JOB_CATEGORY_OPTIONS"
            allow-clear
            placeholder="岗位类别"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-select
            v-model:value="form.workCity"
            :options="WORK_CITY_OPTIONS"
            allow-clear
            placeholder="工作城市"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-select
            v-model:value="form.educationRequirement"
            :options="EDUCATION_OPTIONS"
            allow-clear
            placeholder="学历要求"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-input-number
            v-model:value="form.salaryMin"
            :min="0"
            :precision="0"
            placeholder="最低薪资 (K)"
            style="width: 100%"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-input-number
            v-model:value="form.salaryMax"
            :min="0"
            :precision="0"
            placeholder="最高薪资 (K)"
            style="width: 100%"
          />
        </a-col>
        <a-col :xs="24" :sm="12" :md="8" :lg="6">
          <a-button type="primary" :loading="loading" @click="handleSearch">
            查询
          </a-button>
          <a-button class="reset-btn" @click="handleReset">重置</a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- 列表区 -->
    <div ref="listTopRef">
      <a-card :bordered="false">
        <!-- 加载骨架 -->
        <a-row v-if="loading" :gutter="[16, 16]">
          <a-col v-for="n in 4" :key="n" :xs="24" :md="12">
            <a-card>
              <a-skeleton active :paragraph="{ rows: 4 }" />
            </a-card>
          </a-col>
        </a-row>

        <!-- 加载失败兜底 -->
        <a-result
          v-else-if="loadError"
          status="warning"
          title="岗位加载失败"
          sub-title="网络异常或服务暂时不可用，请稍后重试"
        >
          <template #extra>
            <a-button type="primary" @click="loadJobs">重试</a-button>
          </template>
        </a-result>

        <!-- 无数据 -->
        <a-empty v-else-if="jobList.length === 0" description="暂无符合条件的岗位" />

        <!-- 岗位卡片 -->
        <a-row v-else :gutter="[16, 16]">
          <a-col v-for="job in jobList" :key="job.id" :xs="24" :md="12">
            <a-card hoverable class="job-card" @click="openDetail(job.id)">
              <div class="job-head">
                <a-typography-title
                  :level="5"
                  :ellipsis="true"
                  class="position-title"
                  :content="job.positionName"
                />
                <span class="salary-note">{{ salaryText(job) }}</span>
              </div>
              <a-typography-text
                type="secondary"
                :ellipsis="true"
                class="company-text"
                :content="job.companyName"
              />
              <div class="job-tags">
                <a-tag v-if="job.jobCategory" color="blue">{{ job.jobCategory }}</a-tag>
                <a-tag v-if="job.workCity">{{ job.workCity }}</a-tag>
                <a-tag v-if="job.educationText">{{ job.educationText }}</a-tag>
                <a-tag v-if="job.industry">{{ job.industry }}</a-tag>
              </div>
              <a-typography-paragraph
                v-if="job.jobDescription"
                type="secondary"
                :ellipsis="{ rows: 2 }"
                class="job-desc"
                :content="job.jobDescription"
              />
              <div class="job-footer">
                <span class="publish-time">{{ fmtDate(job.publishTime) }} 发布</span>
                <a-button type="link" size="small" @click.stop="openDetail(job.id)">
                  查看详情
                </a-button>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 分页 -->
        <div v-if="!loading && !loadError && total > 0" class="pagination">
          <a-pagination
            :current="pageNum"
            :page-size="pageSize"
            :total="total"
            :page-size-options="['10', '20']"
            show-size-changer
            :show-total="showTotal"
            @change="handlePageChange"
          />
        </div>
      </a-card>
    </div>

    <!-- 岗位详情抽屉 -->
    <a-drawer
      v-model:open="drawerOpen"
      title="岗位详情"
      :width="640"
      :destroy-on-close="true"
    >
      <a-spin v-if="detailLoading" tip="加载中...">
        <div style="min-height: 240px" />
      </a-spin>

      <a-result
        v-else-if="detailError"
        status="warning"
        title="详情加载失败"
        sub-title="请关闭后重试"
      />

      <template v-else-if="detail">
        <div class="drawer-head">
          <a-typography-title :level="4" class="drawer-position">
            {{ detail.positionName }}
          </a-typography-title>
          <a-tag :color="detail.status === 1 ? 'green' : 'default'">
            {{ detail.status === 1 ? '在招' : '已下架' }}
          </a-tag>
        </div>

        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="公司">
            {{ dash(detail.companyName) }}
          </a-descriptions-item>
          <a-descriptions-item label="行业">
            {{ dash(detail.industry) }}
          </a-descriptions-item>
          <a-descriptions-item label="岗位类别">
            {{ dash(detail.jobCategory) }}
          </a-descriptions-item>
          <a-descriptions-item label="工作城市">
            {{ dash(detail.workCity) }}
          </a-descriptions-item>
          <a-descriptions-item label="学历要求">
            {{ dash(detail.educationText) }}
          </a-descriptions-item>
          <a-descriptions-item label="薪资区间">
            <span class="salary-note">{{ salaryRange(detail) }}</span>
            <span v-if="detail.salaryNote" class="salary-extra">
              （{{ detail.salaryNote }}）
            </span>
          </a-descriptions-item>
          <a-descriptions-item label="发布时间">
            {{ fmtDate(detail.publishTime) }}
          </a-descriptions-item>
          <a-descriptions-item label="网申截止">
            {{ fmtDate(detail.deadline) }}
          </a-descriptions-item>
        </a-descriptions>

        <a-divider orientation="left">岗位描述</a-divider>
        <div class="pre-wrap">{{ dash(detail.jobDescription) }}</div>

        <a-divider orientation="left">任职要求</a-divider>
        <div class="pre-wrap">{{ dash(detail.jobRequirement) }}</div>

        <a-divider orientation="left">来源</a-divider>
        <div class="source-line">
          <span>{{ dash(detail.sourceChannel) }}</span>
          <a
            v-if="detail.sourceUrl"
            :href="detail.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="source-link"
          >
            查看原文
          </a>
        </div>

        <div class="drawer-footer">
          <a-button type="primary" block @click="analyzeByAi">
            让 AI 分析这个岗位
          </a-button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<style scoped>
.job-square {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reset-btn {
  margin-left: 8px;
}

/* 岗位卡片 */
.job-card {
  cursor: pointer;
  height: 100%;
}

.job-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.position-title {
  flex: 1 1 auto;
  min-width: 0;
  margin-bottom: 0 !important;
}

.salary-note {
  flex: 0 0 auto;
  font-size: 15px;
  font-weight: 600;
  color: #cf1322;
  white-space: nowrap;
}

.salary-extra {
  color: #8c8c8c;
  font-weight: 400;
}

.company-text {
  display: block;
  margin-top: 6px;
}

.job-tags {
  margin-top: 10px;
}

.job-tags .ant-tag {
  margin-right: 8px;
  margin-bottom: 4px;
}

.job-desc {
  margin-top: 8px;
  margin-bottom: 4px !important;
}

.job-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.publish-time {
  font-size: 12px;
  color: #8c8c8c;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 详情抽屉 */
.drawer-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.drawer-position {
  margin-bottom: 0 !important;
}

.pre-wrap {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}

.source-line {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #595959;
}

.source-link {
  color: #1677ff;
}

.drawer-footer {
  position: sticky;
  bottom: -24px;
  z-index: 1;
  margin: 24px -24px -24px;
  padding: 12px 24px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}
</style>
