<script setup lang="ts">
/**
 * 能力画像
 *
 * 展示我的能力雷达图与成长趋势：
 * - 上部"能力雷达图 + 维度得分"：getMyAbility() 各维度得分绘制雷达图
 *   （严格按 ABILITY_DIMENSIONS 五维度顺序，axisMax=100，深蓝 #1677ff），
 *   后端返回但不在标准五维度内的维度追加到列表展示；无数据空态兜底。
 * - 下部"能力成长趋势"：维度下拉切换，调 getAbilityTrend(dimension)
 *   绘制平滑折线图（x=snapshotDate，y=dimensionScore 0-100，数据点带 label）。
 *
 * 图表按需引入 echarts（echarts/core + CanvasRenderer + RadarChart/LineChart
 * + TooltipComponent/GridComponent/LegendComponent），打包体积可控。
 */

import { onMounted, ref, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, RadarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

import { getAbilityTrend, getMyAbility } from '@/api/ability'
import type { AbilityProfile, AbilityTrendPoint } from '@/types/business'
import { ABILITY_DIMENSIONS } from '@/types/business'

use([
  CanvasRenderer,
  LineChart,
  RadarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
])

/* --------------------------------- 能力雷达图 -------------------------------- */

/** 雷达图数据加载状态 */
const radarLoading = ref(false)
/** 能力画像列表 */
const abilityList = ref<AbilityProfile[]>([])

/** 标准五维度得分（严格按 ABILITY_DIMENSIONS 顺序；缺失记 0） */
const radarValues = ref<number[]>([])

/** 雷达图 option */
const radarOption = ref<Record<string, unknown>>({})

/** 维度得分列表行（含追加的非标准维度与评语） */
const scoreRows = ref<{ dimension: string; score: number; evaluation: string }[]>([])

/** 是否无能力数据（用于空态） */
const abilityEmpty = ref(true)

/**
 * 构建雷达图 option：五维度 indicator max=100，深蓝 #1677ff。
 */
function buildRadarOption(): Record<string, unknown> {
  return {
    tooltip: {},
    legend: { data: ['当前能力'] },
    radar: {
      indicator: ABILITY_DIMENSIONS.map((name) => ({ name, max: 100 })),
      radius: '65%',
    },
    series: [
      {
        name: '当前能力',
        type: 'radar',
        data: [
          {
            value: radarValues.value,
            name: '当前能力',
            areaStyle: { color: 'rgba(22, 119, 255, 0.25)' },
            lineStyle: { color: '#1677ff', width: 2 },
            itemStyle: { color: '#1677ff' },
          },
        ],
      },
    ],
  }
}

/**
 * 加载我的能力画像：
 * - standardRows：标准五维度按固定顺序；
 * - extraRows：非标准维度按返回顺序追加；
 * - 任一数据缺失维度记 0 并保持五边雷达图不塌陷。
 */
function applyAbility(list: AbilityProfile[]): void {
  const radarRow = ABILITY_DIMENSIONS.map((name) => {
    const hit = list.find((item) => item.dimension === name)
    return hit?.dimensionScore ?? 0
  })
  radarValues.value = radarRow

  const rows: { dimension: string; score: number; evaluation: string }[] = []
  ABILITY_DIMENSIONS.forEach((name) => {
    const hit = list.find((item) => item.dimension === name)
    rows.push({
      dimension: name,
      score: hit?.dimensionScore ?? 0,
      evaluation: hit?.evaluation ?? '',
    })
  })
  list.forEach((item) => {
    if (!ABILITY_DIMENSIONS.includes(item.dimension as never)) {
      rows.push({
        dimension: String(item.dimension),
        score: item.dimensionScore,
        evaluation: item.evaluation ?? '',
      })
    }
  })
  scoreRows.value = rows
  abilityEmpty.value = list.length === 0
  radarOption.value = buildRadarOption()
}

/**
 * 加载能力画像；失败置空态兜底不白屏。
 */
async function loadAbility(): Promise<void> {
  radarLoading.value = true
  try {
    const res = await getMyAbility()
    applyAbility(res.data ?? [])
  } catch (error) {
    console.warn('[ability] 能力画像加载失败:', error)
    abilityList.value = []
    abilityEmpty.value = true
  } finally {
    radarLoading.value = false
  }
}

/* --------------------------------- 成长趋势 -------------------------------- */

/** 趋势图数据加载状态 */
const trendLoading = ref(false)
/** 当前选中的趋势维度（默认第一项） */
const trendDimension = ref<string>(ABILITY_DIMENSIONS[0])
/** 趋势数据点 */
const trendPoints = ref<AbilityTrendPoint[]>([])

/** 趋势图 option */
const trendOption = ref<Record<string, unknown>>({})

/** 是否无趋势数据（用于空态） */
const trendEmpty = ref(true)

/**
 * 构建趋势折线图 option：平滑曲线 + 数据点 label，y 轴 0-100。
 */
function buildTrendOption(): Record<string, unknown> {
  const points = trendPoints.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 24, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((p) => p.snapshotDate || ''),
    },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [
      {
        name: trendDimension.value,
        type: 'line',
        data: points.map((p) => p.dimensionScore),
        smooth: true,
        symbolSize: 8,
        lineStyle: { color: '#1677ff', width: 2 },
        itemStyle: { color: '#1677ff' },
        label: { show: true, position: 'top', fontSize: 12, color: '#595959' },
      },
    ],
  }
}

/**
 * 加载指定维度成长曲线；无数据置空态。
 */
async function loadTrend(): Promise<void> {
  trendLoading.value = true
  try {
    const res = await getAbilityTrend(trendDimension.value)
    trendPoints.value = res.data ?? []
    trendEmpty.value = trendPoints.value.length === 0
    trendOption.value = buildTrendOption()
  } catch (error) {
    console.warn('[ability] 能力趋势加载失败:', error)
    trendPoints.value = []
    trendEmpty.value = true
  } finally {
    trendLoading.value = false
  }
}

/** 切换维度即重请求趋势 */
watch(trendDimension, () => {
  loadTrend()
})

onMounted(() => {
  loadAbility()
  loadTrend()
})
</script>

<template>
  <div class="ability-page">
    <!-- 上部：能力雷达图 + 维度得分 -->
    <a-card :bordered="false" :loading="radarLoading" title="能力雷达图与维度得分">
      <a-empty
        v-if="!radarLoading && abilityEmpty"
        description="暂无能力画像，完成模拟面试后由 AI 生成"
      />
      <a-row v-else :gutter="24">
        <a-col :xs="24" :md="12">
          <div class="radar-chart">
            <v-chart :option="radarOption" autoresize />
          </div>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-list size="small" class="score-list">
            <a-list-item v-for="row in scoreRows" :key="row.dimension">
              <a-list-item-meta :title="row.dimension">
                <template #description>
                  <span v-if="row.evaluation">{{ row.evaluation }}</span>
                  <span v-else class="no-eval">暂无评语</span>
                </template>
              </a-list-item-meta>
              <div class="score-value">{{ row.score }}</div>
            </a-list-item>
          </a-list>
        </a-col>
      </a-row>
    </a-card>

    <!-- 下部：能力成长趋势 -->
    <a-card :bordered="false" :loading="trendLoading" title="能力成长趋势">
      <div class="trend-head">
        <a-select
          v-model:value="trendDimension"
          class="trend-select"
          :options="ABILITY_DIMENSIONS.map((d) => ({ label: d, value: d }))"
          placeholder="选择维度"
        />
      </div>
      <a-empty
        v-if="!trendLoading && trendEmpty"
        description="该维度暂无成长记录"
      />
      <div v-else class="trend-chart">
        <v-chart :option="trendOption" autoresize />
      </div>
    </a-card>
  </div>
</template>

<style scoped>
.ability-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.radar-chart,
.trend-chart {
  width: 100%;
  height: 400px;
}

.score-list {
  max-height: 400px;
  overflow-y: auto;
}

.score-value {
  font-size: 18px;
  font-weight: 600;
  color: #1677ff;
}

.no-eval {
  color: #bfbfbf;
}

.trend-head {
  margin-bottom: 12px;
}

.trend-select {
  width: 220px;
}
</style>