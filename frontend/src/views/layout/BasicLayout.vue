<script setup lang="ts">
/**
 * 主布局
 *
 * 左侧导航 + 顶部头部 + 内容区，支持菜单折叠。
 */

import { ref } from 'vue'

import HeaderBar from '@/views/layout/components/HeaderBar.vue'
import SideMenu from '@/views/layout/components/SideMenu.vue'

/** 侧边栏折叠状态 */
const collapsed = ref(false)
</script>

<template>
  <a-layout class="layout-root">
    <a-layout-sider v-model:collapsed="collapsed" :trigger="null" collapsible theme="dark" width="220">
      <div class="layout-logo">{{ collapsed ? '校园' : '校园招聘AI平台' }}</div>
      <SideMenu />
    </a-layout-sider>

    <a-layout>
      <HeaderBar v-model:collapsed="collapsed" />

      <a-layout-content class="layout-content">
        <router-view />
      </a-layout-content>

      <a-layout-footer class="layout-footer">
        校园招聘AI平台 ©2026 campus-recruit-ai-platform
      </a-layout-footer>
    </a-layout>
  </a-layout>
</template>

<style scoped>
.layout-root {
  min-height: 100vh;
}

.layout-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  overflow: hidden;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.layout-content {
  margin: 16px;
  padding: 16px;
  min-height: calc(100vh - 56px - 70px - 32px);
  background: #fff;
  border-radius: 8px;
}

.layout-footer {
  padding: 12px 16px;
  text-align: center;
  color: #8c8c8c;
}
</style>
