<script setup lang="ts">
/**
 * 求职画像
 *
 * 用户求职画像的查看与维护：onMounted 加载 getMyProfile()，
 * - 尚未填写（data 为 null）时展示空态引导，点击"立即填写"进入编辑；
 * - 已填写时以 a-descriptions 摘要展示，可进入编辑直铺表单；
 * - 保存走 saveMyProfile（字段级更新语义），成功刷新展示区，
 *   失败以 a-result 警告兜底，不白屏。
 */

import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'

import { getMyProfile, saveMyProfile } from '@/api/profile'
import type { EducationLevel, UserProfile, UserProfileSaveParams } from '@/types/business'

/** 意向城市选项 */
const CITY_OPTIONS = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉', '西安', '其他']

/** 学历选项（value 对应 EducationLevel 枚举） */
const EDUCATION_OPTIONS: { value: EducationLevel; label: string }[] = [
  { value: 0, label: '其他' },
  { value: 1, label: '本科' },
  { value: 2, label: '硕士' },
  { value: 3, label: '博士' },
]

/** 毕业年份范围：2000 ~ 当前年 + 1 */
const YEAR_OPTIONS: number[] = (() => {
  const current = new Date().getFullYear()
  const years: number[] = []
  for (let year = 2000; year <= current + 1; year += 1) {
    years.push(year)
  }
  return years
})()

/** 描述项文本兜底 */
function displayText(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  return String(value)
}

/** 学历枚举转中文 */
function educationLabel(value?: EducationLevel | number): string {
  return EDUCATION_OPTIONS.find((item) => item.value === value)?.label ?? '-'
}

/* --------------------------------- 状态与数据 -------------------------------- */

/** 加载状态 */
const loading = ref(false)
/** 画像数据（null 表示尚未填写） */
const profile = ref<UserProfile | null>(null)
/** 是否处于编辑态 */
const editing = ref(false)
/** 保存是否失败（a-result 兜底） */
const saveFailed = ref(false)
/** 保存提交中 */
const saving = ref(false)

/** 画像表单引用 */
const formRef = ref<FormInstance>()

/** 画像编辑表单（初始全空，回显时填充） */
const form = reactive<UserProfileSaveParams>({
  targetPosition: '',
  targetIndustry: '',
  cityPreference: '',
  education: undefined,
  school: '',
  major: '',
  graduationYear: undefined,
  skillTags: [],
  careerIntention: '',
  selfEvaluation: '',
})

/** 表单校验规则：当前全字段选填，可后续按需收紧 */
const formRules: Record<string, Rule[]> = {}

/**
 * 用画像数据回填表单。
 *
 * @param data 画像数据（非 null）
 */
function fillForm(data: UserProfile): void {
  form.targetPosition = data.targetPosition ?? ''
  form.targetIndustry = data.targetIndustry ?? ''
  form.cityPreference = data.cityPreference ?? ''
  form.education = data.education
  form.school = data.school ?? ''
  form.major = data.major ?? ''
  form.graduationYear = data.graduationYear
  form.skillTags = data.skillTags ?? []
  form.careerIntention = data.careerIntention ?? ''
  form.selfEvaluation = data.selfEvaluation ?? ''
}

/** 展示用摘要行列表 */
const summaryItems = computed<
  { label: string; text: string; isTags?: boolean }[]
>(() => {
  const p = profile.value
  if (!p) {
    return []
  }
  return [
    { label: '目标岗位', text: displayText(p.targetPosition) },
    { label: '目标行业', text: displayText(p.targetIndustry) },
    { label: '意向城市', text: displayText(p.cityPreference) },
    { label: '学历', text: educationLabel(p.education) },
    { label: '学校', text: displayText(p.school) },
    { label: '专业', text: displayText(p.major) },
    { label: '毕业年份', text: p.graduationYear ? displayText(p.graduationYear) : '-' },
    { label: '技能标签', text: '', isTags: true },
    { label: '求职意向', text: displayText(p.careerIntention) },
    { label: '自我评价', text: displayText(p.selfEvaluation) },
  ]
})

/**
 * 加载我的画像；data null 时展示空态，异常时也以空态兜底避免白屏。
 */
async function loadProfile(): Promise<void> {
  loading.value = true
  try {
    const res = await getMyProfile()
    profile.value = res.data
  } catch (error) {
    console.warn('[profile] 画像加载失败:', error)
    profile.value = null
    saveFailed.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 进入编辑态：回填当前画像（可为空）。
 */
function startEdit(): void {
  saveFailed.value = false
  if (profile.value) {
    fillForm(profile.value)
  }
  editing.value = true
}

/**
 * 取消编辑，回到展示 / 空态。
 */
function cancelEdit(): void {
  editing.value = false
  saveFailed.value = false
}

/**
 * 收集表单为保存参数：空串按"不修改"省略；skillTags 按后端语义，
 * 空数组也显式传 []（清空标签），不传 undefined。
 */
function buildParams(): UserProfileSaveParams {
  const params: UserProfileSaveParams = {}
  if (form.targetPosition?.trim()) {
    params.targetPosition = form.targetPosition.trim()
  }
  if (form.targetIndustry?.trim()) {
    params.targetIndustry = form.targetIndustry.trim()
  }
  if (form.cityPreference) {
    params.cityPreference = form.cityPreference
  }
  if (form.education !== undefined && form.education !== null) {
    params.education = form.education
  }
  if (form.school?.trim()) {
    params.school = form.school.trim()
  }
  if (form.major?.trim()) {
    params.major = form.major.trim()
  }
  if (form.graduationYear !== undefined && form.graduationYear !== null) {
    params.graduationYear = form.graduationYear
  }
  params.skillTags = form.skillTags ?? []
  if (form.careerIntention?.trim()) {
    params.careerIntention = form.careerIntention.trim()
  }
  if (form.selfEvaluation?.trim()) {
    params.selfEvaluation = form.selfEvaluation.trim()
  }
  return params
}

/**
 * 保存画像：成功刷新展示区；失败进入 a-result 兜底。
 */
async function handleSubmit(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  saveFailed.value = false
  try {
    const res = await saveMyProfile(buildParams())
    profile.value = res.data
    message.success('画像已保存')
    editing.value = false
  } catch (error) {
    console.warn('[profile] 画像保存失败:', error)
    saveFailed.value = true
  } finally {
    saving.value = false
  }
}

/**
 * 保存失败后返回编辑态重试。
 */
function retryEdit(): void {
  saveFailed.value = false
  editing.value = true
}

onMounted(() => {
  loadProfile()
})
</script>

<template>
  <div class="profile-page">
    <!-- 保存失败兜底 -->
    <a-card v-if="saveFailed" :bordered="false" class="panel-card">
      <a-result
        status="warning"
        title="画像保存失败"
        sub-title="请稍后重试，或检查网络连接后重新提交"
      >
        <template #extra>
          <a-button type="primary" @click="retryEdit">返回编辑重试</a-button>
        </template>
      </a-result>
    </a-card>

    <!-- 加载态 -->
    <a-card
      v-else-if="loading"
      :bordered="false"
      :loading="loading"
      title="求职画像"
      class="panel-card"
    />

    <!-- 空态：尚未填写画像 -->
    <a-card
      v-else-if="!editing && !profile"
      :bordered="false"
      title="求职画像"
      class="panel-card"
    >
      <a-empty description="完善求职画像，AI 将提供更精准的岗位分析与面试建议">
        <a-button type="primary" @click="startEdit">立即填写</a-button>
      </a-empty>
    </a-card>

    <!-- 展示态：画像摘要 -->
    <a-card
      v-else-if="!editing && profile"
      :bordered="false"
      title="求职画像"
      extra="更新于最近一次保存"
      class="panel-card"
    >
      <a-descriptions :column="2" size="small" bordered>
        <a-descriptions-item v-for="item in summaryItems" :key="item.label" :label="item.label">
          <template v-if="item.isTags">
            <a-tag
              v-for="tag in profile?.skillTags ?? []"
              :key="tag"
              color="blue"
              class="skill-tag"
            >
              {{ tag }}
            </a-tag>
            <span v-if="!(profile?.skillTags?.length)">-</span>
          </template>
          <span v-else>{{ item.text }}</span>
        </a-descriptions-item>
      </a-descriptions>
      <div class="form-actions">
        <a-button type="primary" @click="startEdit">编辑画像</a-button>
      </div>
    </a-card>

    <!-- 编辑态：直铺表单 + 底部按钮组 -->
    <a-card
      v-else
      :bordered="false"
      title="求职画像"
      class="panel-card"
    >
      <a-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        layout="vertical"
        class="profile-form"
      >
        <a-form-item label="目标岗位" name="targetPosition">
          <a-input v-model:value="form.targetPosition" placeholder="如 后端开发工程师" />
        </a-form-item>

        <a-form-item label="目标行业" name="targetIndustry">
          <a-input v-model:value="form.targetIndustry" placeholder="如 互联网" />
        </a-form-item>

        <a-form-item label="意向城市" name="cityPreference">
          <a-select
            v-model:value="form.cityPreference"
            :options="CITY_OPTIONS.map((city) => ({ value: city, label: city }))"
            placeholder="请选择意向城市"
            allow-clear
          />
        </a-form-item>

        <a-form-item label="学历" name="education">
          <a-select
            v-model:value="form.education"
            :options="EDUCATION_OPTIONS"
            placeholder="请选择学历"
          />
        </a-form-item>

        <a-form-item label="学校" name="school">
          <a-input v-model:value="form.school" placeholder="请输入学校名称" />
        </a-form-item>

        <a-form-item label="专业" name="major">
          <a-input v-model:value="form.major" placeholder="请输入所学专业" />
        </a-form-item>

        <a-form-item label="毕业年份" name="graduationYear">
          <a-select
            v-model:value="form.graduationYear"
            :options="YEAR_OPTIONS.map((year) => ({ value: year, label: String(year) }))"
            placeholder="请选择毕业年份"
          />
        </a-form-item>

        <a-form-item label="技能标签" name="skillTags">
          <a-select
            v-model:value="form.skillTags"
            mode="tags"
            :open="false"
            placeholder="输入后回车添加，如 Java、Spring、Redis、Python"
            allow-clear
          />
        </a-form-item>

        <a-form-item label="求职意向" name="careerIntention">
          <a-textarea
            v-model:value="form.careerIntention"
            :rows="3"
            placeholder="简述意向岗位方向、职业规划等"
          />
        </a-form-item>

        <a-form-item label="自我评价" name="selfEvaluation">
          <a-textarea
            v-model:value="form.selfEvaluation"
            :rows="4"
            placeholder="简述个人优势、项目经历与亮点"
          />
        </a-form-item>

        <div class="form-actions">
          <a-button :disabled="saving" @click="cancelEdit">取消</a-button>
          <a-button type="primary" :loading="saving" @click="handleSubmit">保存</a-button>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-card {
  background: #fff;
  border-radius: 8px;
}

.profile-form {
  max-width: 720px;
}

.skill-tag {
  margin-right: 8px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>