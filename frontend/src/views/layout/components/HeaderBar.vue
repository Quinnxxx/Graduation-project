<script setup lang="ts">
/**
 * 顶部头部
 *
 * 左侧折叠开关，右侧用户下拉（个人信息 / 退出登录）。
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

import { useUserStore } from '@/store/modules/user'

/** 折叠状态（v-model:collapsed 双向绑定） */
const props = defineProps<{
  collapsed: boolean
}>()

/** 折叠状态变更事件 */
const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
}>()

const router = useRouter()
const userStore = useUserStore()

/** 当前用户展示名：昵称 > 用户名 > 占位 */
const displayName = computed<string>(
  () => userStore.userInfo?.nickname || userStore.userInfo?.username || '未登录',
)

/**
 * 切换折叠状态
 */
function toggleCollapsed(): void {
  emit('update:collapsed', !props.collapsed)
}

/**
 * 退出登录
 */
async function handleLogout(): Promise<void> {
  userStore.logout()
  message.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <a-layout-header class="header-bar">
    <div class="header-left">
      <a-button
        type="text"
        class="header-trigger"
        @click="toggleCollapsed"
      >
        <MenuUnfoldOutlined v-if="collapsed" />
        <MenuFoldOutlined v-else />
      </a-button>
    </div>

    <div class="header-right">
      <a-dropdown placement="bottomRight">
        <div class="header-user">
          <a-avatar size="small" style="background-color: #1677ff">
            <UserOutlined />
          </a-avatar>
          <span class="header-username">{{ displayName }}</span>
        </div>
        <template #overlay>
          <a-menu>
            <a-menu-item key="logout" @click="handleLogout">
              <LogoutOutlined />
              退出登录
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </a-layout-header>
</template>

<style scoped>
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
}

.header-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  font-size: 16px;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  cursor: pointer;
}

.header-username {
  max-width: 120px;
  overflow: hidden;
  font-size: 14px;
  color: #1a1a1a;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
