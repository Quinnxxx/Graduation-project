<script setup lang="ts">
/**
 * 简历管理
 *
 * 当前登录用户简历记录的增删改查：
 * - 顶部提供"新建简历"入口与分页（每页 10/20 可切换）；
 * - 新建弹窗校验标题与原文必填，创建成功后刷新第一页；
 * - 列表展示标题、处理状态、目标岗位、创建时间与操作按钮；
 * - 详情抽屉按 id 拉取完整记录，原文 / 优化后文本分栏（pre-wrap），
 *   优化建议存在时以 a-alert 展示；
 * - 编辑弹窗按后端 ResumeUpdateDTO 契约实现：resumeTitle 只读不可改，
 *   仅 optimizedContent / optimizationSuggestions / resumeScore /
 *   optimizedScore / status 可编辑，字段级更新（未改动的字段不传）；
 * - 删除经 a-popconfirm 确认后逻辑删除并刷新列表。
 */

import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'

import {
  createResume,
  deleteResume,
  getResumeDetail,
  pageResumes,
  updateResume,
  uploadResumePdf,
} from '@/api/resumes'
import type {
  ResumeRecord,
  ResumeSaveParams,
  ResumeUpdateParams,
} from '@/types/business'

/** 空值兜底为 “-” */
function dash(value: unknown): string {
  return value === null || value === undefined || value === '' ? '-' : String(value)
}

/** 日期格式化为 YYYY-MM-DD；无法解析或为空时回退为 “-” */
function fmtDate(value?: string): string {
  if (!value) {
    return '-'
  }
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD') : String(value)
}

/* --------------------------------- 列表与分页 -------------------------------- */

/** 当前页码 */
const pageNum = ref(1)
/** 每页条数 */
const pageSize = ref(10)
/** 总记录数 */
const total = ref(0)
/** 当前页简历列表 */
const list = ref<ResumeRecord[]>([])
/** 列表加载状态 */
const loading = ref(false)
/** 列表加载失败标记（a-result 兜底） */
const loadError = ref(false)

/**
 * 加载当前页简历列表；失败置 loadError，由 a-result 兜底不白屏。
 */
async function loadList(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    const res = await pageResumes({ pageNum: pageNum.value, pageSize: pageSize.value })
    list.value = res.data.list ?? []
    total.value = res.data.total ?? 0
  } catch (error) {
    console.warn('[resume] 简历列表加载失败:', error)
    list.value = []
    total.value = 0
    loadError.value = true
  } finally {
    loading.value = false
  }
}

/** 分页总数文案 */
function showTotal(t: number): string {
  return `共 ${t} 条`
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

/* --------------------------------- 新建弹窗 -------------------------------- */

/** 新建弹窗显隐 */
const createOpen = ref(false)
/** 新建提交中 */
const creating = ref(false)
/** 新建表单引用 */
const createFormRef = ref<FormInstance>()

/** 新建表单数据 */
const createForm = reactive<ResumeSaveParams>({
  resumeTitle: '',
  targetPositionName: '',
  originalContent: '',
})

/** 新建表单校验规则 */
const createRules = {
  resumeTitle: [{ required: true, message: '请输入简历标题', trigger: 'blur' }],
  originalContent: [{ required: true, message: '请输入简历原文', trigger: 'blur' }],
}

/**
 * 打开新建弹窗：表单重置为空。
 */
function openCreate(): void {
  createFormRef.value?.resetFields()
  // 文件字段非 a-form-item，resetFields 不会清空，需手动重置
  createForm.fileName = undefined
  createForm.filePath = undefined
  createForm.fileSize = undefined
  createOpen.value = true
}

/** 简历 PDF 上传中 */
const uploading = ref(false)

/**
 * PDF 选择处理：校验扩展名与大小后调上传接口，成功后回填表单并自动填充原文。
 *
 * 始终返回 false 阻止 a-upload 默认上传，上传动作由本函数自行完成。
 *
 * @param file 用户选择的文件
 * @returns 是否阻止默认上传（恒为 false）
 */
async function handlePdfUpload(file: File): Promise<boolean> {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    message.warning('仅支持上传 PDF 文件')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    message.warning('PDF 文件不能超过 5MB')
    return false
  }
  uploading.value = true
  try {
    const res = await uploadResumePdf(file)
    createForm.originalContent = res.data.text || ''
    createForm.fileName = res.data.fileName
    createForm.filePath = res.data.filePath
    createForm.fileSize = res.data.fileSize
    message.success('PDF 解析成功，简历原文已自动填充，可继续编辑')
  } catch (error) {
    // 业务错误已由请求层统一提示
    console.warn('[resume] PDF 上传失败:', error)
  } finally {
    uploading.value = false
  }
  return false
}

/**
 * 提交创建：成功后提示并刷新第一页。
 */
async function handleCreate(): Promise<void> {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    await createResume({
      resumeTitle: createForm.resumeTitle.trim(),
      originalContent: createForm.originalContent,
      targetPositionName: createForm.targetPositionName?.trim() || undefined,
      // PDF 上传后回填的文件字段，随创建请求落库
      fileName: createForm.fileName,
      filePath: createForm.filePath,
      fileSize: createForm.fileSize,
    })
    message.success('简历创建成功')
    createOpen.value = false
    pageNum.value = 1
    await loadList()
  } catch (error) {
    // 业务错误已由请求层统一提示
    console.warn('[resume] 简历创建失败:', error)
  } finally {
    creating.value = false
  }
}

/* --------------------------------- 详情抽屉 -------------------------------- */

/** 详情抽屉显隐 */
const drawerOpen = ref(false)
/** 详情加载状态 */
const detailLoading = ref(false)
/** 详情加载失败标记 */
const detailError = ref(false)
/** 当前查看的简历详情 */
const detail = ref<ResumeRecord | null>(null)

/**
 * 打开简历详情抽屉并按 id 拉取完整记录。
 *
 * @param id 简历记录 ID
 */
async function openDetail(id: number): Promise<void> {
  drawerOpen.value = true
  detail.value = null
  detailError.value = false
  detailLoading.value = true
  try {
    const res = await getResumeDetail(id)
    detail.value = res.data
  } catch (error) {
    console.warn('[resume] 简历详情加载失败:', error)
    detailError.value = true
  } finally {
    detailLoading.value = false
  }
}

/* --------------------------------- 编辑弹窗 -------------------------------- */

/** 编辑弹窗显隐 */
const editOpen = ref(false)
/** 编辑提交中 */
const editing = ref(false)
/** 编辑表单引用 */
const editFormRef = ref<FormInstance>()

/** 当前编辑的简历记录 ID */
const editId = ref(0)
/** 编辑弹窗中的标题（只读展示，不可修改） */
const editTitle = ref('')
/** 编辑原始值快照（用于字段级更新：未改动的字段不传） */
const editOriginal = reactive<ResumeUpdateParams>({})

/** 编辑表单数据 */
const editForm = reactive<ResumeUpdateParams>({})

/**
 * 打开编辑弹窗：按 id 拉取最新详情回填可编辑字段，
 * 记录原始值快照用于字段级更新 diff。
 *
 * @param id 简历记录 ID
 */
async function openEdit(id: number): Promise<void> {
  editOpen.value = true
  editId.value = id
  editTitle.value = ''
  // 清空表单与快照（显式重置全部可编辑字段）
  editForm.optimizedContent = undefined
  editForm.optimizationSuggestions = undefined
  editForm.resumeScore = undefined
  editForm.optimizedScore = undefined
  editForm.status = undefined
  editOriginal.optimizedContent = undefined
  editOriginal.optimizationSuggestions = undefined
  editOriginal.resumeScore = undefined
  editOriginal.optimizedScore = undefined
  editOriginal.status = undefined
  editError.value = false
  try {
    const res = await getResumeDetail(id)
    const data = res.data
    editTitle.value = data.resumeTitle
    editForm.optimizedContent = data.optimizedContent
    editForm.optimizationSuggestions = data.optimizationSuggestions
    editForm.resumeScore = data.resumeScore
    editForm.optimizedScore = data.optimizedScore
    editForm.status = data.status
    Object.assign(editOriginal, {
      optimizedContent: data.optimizedContent,
      optimizationSuggestions: data.optimizationSuggestions,
      resumeScore: data.resumeScore,
      optimizedScore: data.optimizedScore,
      status: data.status,
    })
  } catch (error) {
    console.warn('[resume] 编辑表单加载失败:', error)
    editError.value = true
  }
}

/** 编辑表单加载失败标记 */
const editError = ref(false)

/**
 * 构造字段级更新参数：仅包含与原始快照不一致的字段，
 * 未改动的字段不传（后端 null=不修改）。
 */
function buildUpdateParams(): ResumeUpdateParams {
  const params: ResumeUpdateParams = {}
  if (editForm.optimizedContent !== editOriginal.optimizedContent) {
    params.optimizedContent = editForm.optimizedContent
  }
  if (editForm.optimizationSuggestions !== editOriginal.optimizationSuggestions) {
    params.optimizationSuggestions = editForm.optimizationSuggestions
  }
  if (editForm.resumeScore !== editOriginal.resumeScore) {
    params.resumeScore = editForm.resumeScore
  }
  if (editForm.optimizedScore !== editOriginal.optimizedScore) {
    params.optimizedScore = editForm.optimizedScore
  }
  if (editForm.status !== editOriginal.status) {
    params.status = editForm.status
  }
  return params
}

/**
 * 提交编辑：仅传改动字段，成功后提示并刷新列表。
 */
async function handleEdit(): Promise<void> {
  try {
    await editFormRef.value?.validate()
  } catch {
    return
  }

  const params = buildUpdateParams()
  if (Object.keys(params).length === 0) {
    message.info('未检测到改动')
    editOpen.value = false
    return
  }

  editing.value = true
  try {
    await updateResume(editId.value, params)
    message.success('简历已更新')
    editOpen.value = false
    await loadList()
  } catch (error) {
    console.warn('[resume] 简历更新失败:', error)
  } finally {
    editing.value = false
  }
}

/* --------------------------------- 删除 --------------------------------- */

/** 删除中的记录 ID（避免重复点击） */
const deletingId = ref<number | null>(null)

/**
 * 删除简历记录（逻辑删除），成功后刷新当前页。
 *
 * @param id 简历记录 ID
 */
async function handleDelete(id: number): Promise<void> {
  deletingId.value = id
  try {
    await deleteResume(id)
    // 当前页删空后回退一页，避免停留空页
    if (list.value.length === 1 && pageNum.value > 1) {
      pageNum.value -= 1
    }
    await loadList()
    message.success('简历已删除')
  } catch (error) {
    console.warn('[resume] 简历删除失败:', error)
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  loadList()
})
</script>

<template>
  <div class="resume-page">
    <!-- 顶部操作区 -->
    <a-card :bordered="false" class="head-card">
      <div class="head-bar">
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          新建简历
        </a-button>
        <span class="head-tip">维护个人简历，AI 优化结果将回写至此</span>
      </div>
    </a-card>

    <!-- 列表区 -->
    <a-card :bordered="false">
      <a-spin v-if="loading"><div class="spin-wrap" /></a-spin>

      <a-result
        v-else-if="loadError"
        status="warning"
        title="简历列表加载失败"
        sub-title="网络异常或服务暂时不可用，请稍后重试"
      >
        <template #extra>
          <a-button type="primary" @click="loadList">重试</a-button>
        </template>
      </a-result>

      <a-empty v-else-if="list.length === 0" description="暂无简历记录" />

      <template v-else>
        <a-list :data-source="list" :split="true" item-layout="horizontal">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <div class="resume-title-row">
                    <span class="resume-title">{{ item.resumeTitle }}</span>
                    <a-tag :color="item.status === 1 ? 'green' : 'blue'">
                      {{ item.status === 1 ? '已完成' : '处理中' }}
                    </a-tag>
                  </div>
                </template>
                <template #description>
                  <a-typography-text type="secondary">
                    <span v-if="item.targetPositionName">{{ item.targetPositionName }} · </span>
                    {{ fmtDate(item.createTime) }} 创建
                  </a-typography-text>
                </template>
              </a-list-item-meta>
              <div class="list-actions">
                <a-button type="link" size="small" @click="openDetail(item.id)">查看</a-button>
                <a-button type="link" size="small" @click="openEdit(item.id)">编辑</a-button>
                <a-popconfirm
                  title="确认删除该简历？"
                  ok-text="删除"
                  cancel-text="取消"
                  @confirm="handleDelete(item.id)"
                >
                  <a-button type="link" size="small" danger :loading="deletingId === item.id">
                    删除
                  </a-button>
                </a-popconfirm>
              </div>
            </a-list-item>
          </template>
        </a-list>

        <!-- 分页：show-total 右对齐 -->
        <div class="pagination">
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

    <!-- 新建简历弹窗 -->
    <a-modal
      v-model:open="createOpen"
      title="新建简历"
      :destroy-on-close="true"
      ok-text="创建"
      cancel-text="取消"
      @ok="handleCreate"
      :confirm-loading="creating"
    >
      <a-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        layout="vertical"
        class="create-form"
      >
        <a-form-item label="简历标题" name="resumeTitle">
          <a-input
            v-model:value="createForm.resumeTitle"
            placeholder="如 我的后端开发简历"
            :maxlength="50"
          />
        </a-form-item>
        <a-form-item label="目标岗位（选填）" name="targetPositionName">
          <a-input v-model:value="createForm.targetPositionName" placeholder="如 后端开发工程师" />
        </a-form-item>
        <a-form-item label="上传 PDF 简历（选填）">
          <a-upload
            accept=".pdf"
            :max-count="1"
            :show-upload-list="false"
            :before-upload="handlePdfUpload"
          >
            <a-button :loading="uploading" :disabled="uploading">
              <template #icon>
                <upload-outlined />
              </template>
              选择 PDF 简历
            </a-button>
          </a-upload>
          <div v-if="createForm.fileName" class="upload-file-name">
            已选择：{{ createForm.fileName }}（原文已自动填充，可直接修改）
          </div>
        </a-form-item>
        <a-form-item label="简历原文" name="originalContent">
          <a-textarea
            v-model:value="createForm.originalContent"
            :rows="12"
            placeholder="粘贴简历全文，供 AI 分析与优化"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:open="drawerOpen"
      title="简历详情"
      :width="720"
      :destroy-on-close="true"
    >
      <a-spin v-if="detailLoading" tip="加载中...">
        <div class="spin-wrap" />
      </a-spin>

      <a-result
        v-else-if="detailError"
        status="warning"
        title="详情加载失败"
        sub-title="请关闭后重试"
      />

      <template v-else-if="detail">
        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="简历标题">
            {{ dash(detail.resumeTitle) }}
          </a-descriptions-item>
          <a-descriptions-item label="目标岗位">
            {{ dash(detail.targetPositionName) }}
          </a-descriptions-item>
          <a-descriptions-item label="创建时间">
            {{ fmtDate(detail.createTime) }}
          </a-descriptions-item>
          <a-descriptions-item label="更新时间">
            {{ fmtDate(detail.updateTime) }}
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="detail.status === 1 ? 'green' : 'blue'">
              {{ detail.status === 1 ? '已完成' : '处理中' }}
            </a-tag>
          </a-descriptions-item>
        </a-descriptions>

        <a-divider orientation="left">简历原文</a-divider>
        <div class="pre-wrap">{{ dash(detail.originalContent) }}</div>

        <a-divider orientation="left">优化后文本</a-divider>
        <div v-if="detail.optimizedContent" class="pre-wrap">
          {{ detail.optimizedContent }}
        </div>
        <a-empty v-else description="尚未优化" />

        <template v-if="detail.optimizationSuggestions">
          <a-divider orientation="left">优化建议</a-divider>
          <a-alert
            type="info"
            :message="detail.optimizationSuggestions"
            show-icon
          />
        </template>
      </template>
    </a-drawer>

    <!-- 编辑弹窗 -->
    <a-modal
      v-model:open="editOpen"
      title="编辑简历（优化结果回填）"
      :destroy-on-close="true"
      ok-text="保存"
      cancel-text="取消"
      @ok="handleEdit"
      :confirm-loading="editing"
    >
      <a-result
        v-if="editError"
        status="warning"
        title="编辑表单加载失败"
        sub-title="请关闭后重试"
      />
      <a-form
        v-else
        ref="editFormRef"
        :model="editForm"
        layout="vertical"
        class="edit-form"
      >
        <a-form-item label="简历标题（不可修改）">
          <a-input v-model:value="editTitle" disabled />
        </a-form-item>
        <a-form-item label="优化后文本">
          <a-textarea
            v-model:value="editForm.optimizedContent"
            :rows="12"
            placeholder="AI 优化后的简历全文；留空表示不修改"
          />
        </a-form-item>
        <a-form-item label="优化建议（JSON）">
          <a-textarea
            v-model:value="editForm.optimizationSuggestions"
            :rows="4"
            placeholder="优化建议 JSON 字符串；留空表示不修改"
          />
        </a-form-item>
        <a-form-item label="优化前评分">
          <a-input-number
            v-model:value="editForm.resumeScore"
            :min="0"
            :max="100"
            :precision="0"
            class="score-input"
            placeholder="0-100"
          />
        </a-form-item>
        <a-form-item label="优化后评分">
          <a-input-number
            v-model:value="editForm.optimizedScore"
            :min="0"
            :max="100"
            :precision="0"
            class="score-input"
            placeholder="0-100"
          />
        </a-form-item>
        <a-form-item label="状态">
          <a-select
            v-model:value="editForm.status"
            :options="[
              { value: 0, label: '处理中' },
              { value: 1, label: '已完成' },
            ]"
            allow-clear
            placeholder="请选择状态"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.resume-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.head-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.head-tip {
  font-size: 13px;
  color: #8c8c8c;
}

.spin-wrap {
  min-height: 240px;
}

.resume-title-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.resume-title {
  font-weight: 600;
  color: #1f2937;
}

.list-actions {
  display: inline-flex;
  align-items: center;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.pre-wrap {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}

.create-form,
.edit-form {
  max-width: 640px;
}

.upload-file-name {
  margin-top: 8px;
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
}

.score-input {
  width: 160px;
}
</style>