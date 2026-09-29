<script setup lang="ts">
/**
 * 应用根组件
 *
 * 全局包裹 a-config-provider 配置中文语言包，渲染路由出口。
 */

import zhCN from 'ant-design-vue/es/locale/zh_CN'
</script>

<template>
  <a-config-provider :locale="zhCN">
    <router-view />
  </a-config-provider>
</template>
