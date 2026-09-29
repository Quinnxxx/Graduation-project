<script setup lang="ts">
/**
 * 侧边栏导航菜单
 *
 * 当前使用静态菜单（图标 + 文字）；菜单项 key 与路由 path 对齐，
 * 后续新增页面时在此同步追加，避免出现点击后 404 的菜单。
 */

import { computed } from 'vue'
import type { Component } from 'vue'
import { useRoute } from 'vue-router'
import {
  AppstoreOutlined,
  FileTextOutlined,
  HomeOutlined,
  RadarChartOutlined,
  RobotOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

const route = useRoute()

/** 当前选中菜单项（与路由路径对齐） */
const selectedKeys = computed<string[]>(() => [route.path])

/** 侧边栏菜单项类型 */
interface MenuItem {
  /** 菜单唯一标识，与路由 path 对齐 */
  key: string
  /** 菜单文案 */
  label: string
  /** 菜单图标组件 */
  icon: Component
}

/** 菜单配置：仅注册已有页面，避免 404 */
const menuItems: MenuItem[] = [
  { key: '/dashboard', label: '工作台', icon: HomeOutlined },
  { key: '/jobs', label: '岗位广场', icon: AppstoreOutlined },
  { key: '/assistant', label: 'AI求职助手', icon: RobotOutlined },
  { key: '/profile', label: '求职画像', icon: UserOutlined },
  { key: '/resumes', label: '简历管理', icon: FileTextOutlined },
  { key: '/ability', label: '能力画像', icon: RadarChartOutlined },
  { key: '/interviews', label: '模拟面试', icon: TeamOutlined },
]
</script>

<template>
  <a-menu theme="dark" mode="inline" :selected-keys="selectedKeys">
    <a-menu-item v-for="item in menuItems" :key="item.key">
      <router-link :to="item.key">
        <component :is="item.icon" />
        <span>{{ item.label }}</span>
      </router-link>
    </a-menu-item>
  </a-menu>
</template>
