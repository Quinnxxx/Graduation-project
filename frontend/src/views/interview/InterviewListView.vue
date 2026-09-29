<script setup lang="ts">
/**
 * 模拟面试记录列表
 *
 * 分页展示我的模拟面试记录，支持按类型筛选（全部/技术面/HR面）：
 * - 顶部"开始面试"弹出创建表单，成功后进入面试进行页；
 * - 列表展示类型/目标/难度/状态/提问数/评分等摘要；
 * - 操作：进行中的记录"进入"进行页，已结束的记录"进入"复盘页；删除经确认后逻辑删除。
 */

import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import dayjs from 'dayjs'

import { createInterview, deleteInterview, pageInterviews } from '@/api/interviews'
import { pageResumes } from '@/api/resumes'
import type {
  InterviewCreateParams,
  InterviewRecord,
  InterviewType,
  ResumeRecord,
} from '@/types/business'

const router = useRouter()

/** 日期格式化为 YYYY-MM-DD */
function fmtDate(value?: string): string {
  if (!value) {
    return '-'
  }
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD') : String(value)
}

/** 面试类型标签元信息 */
const TYPE_META: Record<number, { label: string; color: string }> = {
  1: { label: '技术面', color: 'orange' },
  2: { label: 'HR面', color: 'purple' },
}

/** 难度标签元信息 */
const DIFF_META: Record<number, string> = {
  1: '简单',
  2: '中等',
  3: '困难',
}

/** 状态标签元信息（tag 语义 vs 标签色） */
const STATUS_META: Record<number, { label: string; color: string }> = {
  1: { label: '进行中', color: 'processing' },
  2: { label: '已完成', color: 'green' },
  3: { label: '已中断', color: 'red' },
}

/**
 * 面试类型展示元信息，未知值兜底为技术面。
 */
function typeMeta(type?: InterviewType | number): { label: string; color: string } {
  return TYPE_META[type ?? 1] ?? TYPE_META[1]
}

/* --------------------------------- 列表与分页 -------------------------------- */

/** 当前页码 */
const pageNum = ref(1)
/** 每页条数 */
const pageSize = ref(10)
/** 总记录数 */
const total = ref(0)
/** 当前页面试列表 */
const list = ref<InterviewRecord[]>([])
/** 列表加载状态 */
const loading = ref(false)
/** 列表加载失败标记 */
const loadError = ref(false)
/** 类型筛选：undefined 全部 / 1 技术面 / 2 HR面 */
const filterType = ref<InterviewType | undefined>(undefined)

/** 分页总数文案 */
function showTotal(t: number): string {
  return `共 ${t} 条`
}

/**
 * 加载当前页面试记录；失败置空态兜底不白屏。
 */
async function loadList(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const res = await pageInterviews({
      pageNum: pageNum.value,
      pageSize: pageSize.value,
      interviewType: filterType.value,
    })
    list.value = res.data.list ?? []
    total.value = res.data.total ?? 0
  } catch (error) {
    console.warn('[interview] 面试列表加载失败:', error)
    list.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 类型筛选变化：回到第一页重新加载。
 */
function handleFilterChange(): void {
  pageNum.value = 1
  loadList()
}

/**
 * 分页 / 每页条数变化；切换 pageSize 时回到第一页。
 *
 * @param page 目标页码
 * @param size 目标每页条数
 */
async function handlePageChange(page: number, size: number): Promise<void> {
  const sizeChanged = size !== pageSize.value
  pageSize.value = size
  pageNum.value = sizeChanged ? 1 : page
  await loadList()
}

/* --------------------------------- 创建弹窗 -------------------------------- */

/** 创建弹窗显隐 */
const createOpen = ref(false)
/** 创建提交中 */
const creating = ref(false)
/** 创建表单引用 */
const createFormRef = ref<FormInstance>()

/** 创建表单数据 */
const createForm = reactive<InterviewCreateParams & { firstQuestion: string }>({
  interviewType: 1,
  targetCompany: '',
  targetPosition: '',
  difficultyLevel: 2,
  resumeId: undefined,
  firstQuestion: '',
})

/** 创建表单校验规则 */
const createRules = {
  interviewType: [{ required: true, message: '请选择面试类型', trigger: 'change' }],
}

/** 简历下拉选项列表（创建弹窗选择用，最多前 100 条） */
const resumeList = ref<ResumeRecord[]>([])
/** 简历下拉加载中 */
const resumeLoading = ref(false)

/** 简历下拉选项（value=记录ID，label=简历标题） */
const resumeOptions = computed(() =>
  resumeList.value.map((r) => ({ value: r.id, label: r.resumeTitle })),
)

/**
 * 加载简历下拉选项（前 100 条）；失败置空并提示，不阻断创建。
 */
async function loadResumeOptions(): Promise<void> {
  resumeLoading.value = true
  try {
    const res = await pageResumes({ pageNum: 1, pageSize: 100 })
    resumeList.value = res.data.list ?? []
  } catch (error) {
    console.warn('[interview] 简历选项加载失败:', error)
    resumeList.value = []
  } finally {
    resumeLoading.value = false
  }
}

/**
 * 打开创建弹窗。
 */
function openCreate(): void {
  createFormRef.value?.resetFields()
  createForm.interviewType = 1
  createForm.difficultyLevel = 2
  createForm.resumeId = undefined
  createForm.firstQuestion = ''
  createOpen.value = true
  loadResumeOptions()
}

/**
 * 提交创建：成功后跳转面试进行页（首问经 query 透传，缺省"开始技术面试" / "开始HR面试"）。
 */
async function handleCreate(): Promise<void> {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    const res = await createInterview({
      interviewType: createForm.interviewType as InterviewType,
      targetCompany: createForm.targetCompany?.trim() || undefined,
      targetPosition: createForm.targetPosition?.trim() || undefined,
      difficultyLevel: createForm.difficultyLevel,
      resumeId: createForm.resumeId,
    })
    message.success('面试已创建')
    createOpen.value = false
    // 按面试类型生成首问：技术面 → 含"技术面试"命中 tech 路由；HR面 → 含"hr面试"命中 hr 路由。
    // 不再使用无法区分类型的"开始面试"（该短语不在首次路由表中，会误落 chat 兜底导致失忆）。
    const typeFirstQuestion =
      createForm.interviewType === 2 ? '开始HR面试' : '开始技术面试'
    const first = createForm.firstQuestion?.trim() || typeFirstQuestion
    router.push({
      path: `/interviews/${res.data.id}`,
      query: { first },
    })
  } catch (error) {
    console.warn('[interview] 面试创建失败:', error)
  } finally {
    creating.value = false
  }
}

/* --------------------------------- 操作 --------------------------------- */

/**
 * 进入面试：进行中进进行页，已结束进复盘页。
 *
 * @param id    面试记录 ID
 * @param status 面试状态
 */
function enterInterview(id: number, status?: number): void {
  if (status === 2) {
    router.push(`/interviews/${id}/review`)
  } else {
    router.push(`/interviews/${id}`)
  }
}

/**
 * 删除面试记录，成功后刷新当前页。
 *
 * @param id 面试记录 ID
 */
async function handleDelete(id: number): Promise<void> {
  try {
    await deleteInterview(id)
    if (list.value.length === 1 && pageNum.value > 1) {
      pageNum.value -= 1
    }
    await loadList()
    message.success('面试记录已删除')
  } catch (error) {
    console.warn('[interview] 面试删除失败:', error)
  }
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="interview-list">
    <!-- 顶部操作区 -->
    <a-card :bordered="false" class="head-card">
      <div class="head-bar">
        <a-button type="primary" @click="openCreate">开始面试</a-button>
        <a-select
          v-model:value="filterType"
          class="filter-select"
          placeholder="全部类型"
          allow-clear
          @change="handleFilterChange"
        >
          <a-select-option :value="1">技术面</a-select-option>
          <a-select-option :value="2">HR面</a-select-option>
        </a-select>
      </div>
    </a-card>

    <!-- 列表区 -->
    <a-card :bordered="false">
      <a-spin v-if="loading"><div class="spin-wrap" /></a-spin>

      <a-result
        v-else-if="loadError"
        status="warning"
        title="面试列表加载失败"
        sub-title="网络异常或服务暂时不可用，请稍后重试"
      >
        <template #extra>
          <a-button type="primary" @click="loadList">重试</a-button>
        </template>
      </a-result>

      <a-empty v-else-if="list.length === 0" :description="'暂无模拟面试记录，点击「开始面试」开始练习'" />

      <template v-else>
        <a-table
          :data-source="list"
          :row-key="(r: InterviewRecord) => r.id"
          :pagination="false"
          size="middle"
          :loading="loading"
        >
          <a-table-column title="类型" width="90">
            <template #default="{ record }">
              <a-tag :color="typeMeta(record.interviewType).color">
                {{ typeMeta(record.interviewType).label }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="目标">
            <template #default="{ record }">
              <div class="target-cell">
                <span v-if="record.targetPosition">{{ record.targetPosition }}</span>
                <span v-else class="muted">-</span>
                <span v-if="record.targetCompany" class="muted"> · {{ record.targetCompany }}</span>
              </div>
            </template>
          </a-table-column>
          <a-table-column title="难度" width="80">
            <template #default="{ record }">
              {{ DIFF_META[record.difficultyLevel ?? 2] ?? '-' }}
            </template>
          </a-table-column>
          <a-table-column title="状态" width="90">
            <template #default="{ record }">
              <a-tag :color="STATUS_META[record.status ?? 1]?.color ?? 'default'">
                {{ STATUS_META[record.status ?? 1]?.label ?? '-' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="提问数" width="80" data-index="questionCount">
            <template #default="{ record }">{{ record.questionCount ?? 0 }}</template>
          </a-table-column>
          <a-table-column title="评分" width="80">
            <template #default="{ record }">{{ record.overallScore ?? '-' }}</template>
          </a-table-column>
          <a-table-column title="创建时间" width="120">
            <template #default="{ record }">{{ fmtDate(record.createTime) }}</template>
          </a-table-column>
          <a-table-column title="操作" width="150">
            <template #default="{ record }">
              <a-button type="link" size="small" @click="enterInterview(record.id, record.status)">
                {{ (record.status ?? 1) === 2 ? '复盘' : '进入' }}
              </a-button>
              <a-popconfirm
                title="确认删除该面试记录？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </template>
          </a-table-column>
        </a-table>

        <!-- 分页 -->
        <div v-if="total > 0" class="pagination">
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
      </template>
    </a-card>

    <!-- 创建面试弹窗 -->
    <a-modal
      v-model:open="createOpen"
      title="开始新的模拟面试"
      :destroy-on-close="true"
      ok-text="创建并开始"
      cancel-text="取消"
      :confirm-loading="creating"
      @ok="handleCreate"
    >
      <a-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        layout="vertical"
      >
        <a-form-item label="面试类型" name="interviewType">
          <a-radio-group v-model:value="createForm.interviewType" button-style="radio">
            <a-radio-button :value="1">技术面</a-radio-button>
            <a-radio-button :value="2">HR面</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="目标公司（选填）">
          <a-input
            v-model:value="createForm.targetCompany"
            placeholder="如 字节跳动"
            :maxlength="50"
          />
        </a-form-item>
        <a-form-item label="目标岗位（选填）">
          <a-input
            v-model:value="createForm.targetPosition"
            placeholder="如 后端开发工程师"
            :maxlength="50"
          />
        </a-form-item>
        <a-form-item label="关联简历（选填）">
          <a-select
            v-model:value="createForm.resumeId"
            :options="resumeOptions"
            :loading="resumeLoading"
            placeholder="选择一份已上传的简历（可选）"
            allow-clear
            :disabled="resumeList.length === 0"
          />
          <div v-if="resumeList.length === 0" class="resume-empty-tip">
            暂无已上传简历，可在「简历管理」页先创建
          </div>
        </a-form-item>
        <a-form-item label="难度">
          <a-radio-group v-model:value="createForm.difficultyLevel" button-style="radio">
            <a-radio-button :value="1">简单</a-radio-button>
            <a-radio-button :value="2">中等</a-radio-button>
            <a-radio-button :value="3">困难</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="初始问题（选填）">
          <a-textarea
            v-model:value="createForm.firstQuestion"
            :rows="3"
            placeholder="面试开始时先提出的问题，如自我介绍；留空则按面试类型默认「开始技术面试」/「开始HR面试」"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.interview-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.head-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-select {
  width: 140px;
}

.spin-wrap {
  min-height: 240px;
}

.target-cell {
  color: #1f2937;
}

.muted {
  color: #8c8c8c;
}

.resume-empty-tip {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>