/**
 * 路由配置
 *
 * 路由分类：
 * - 公开路由（meta.public = true）：登录页，无需 token 可访问
 * - 受保护路由：挂载在 BasicLayout 下的业务页面，需 token
 *
 * 权限校验逻辑见 guard.ts（路由守卫）
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

/**
 * 公开路由：登录页
 */
const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: {
      title: '登录',
      public: true,
    },
  },
]

/**
 * 受保护路由：主布局及子页面
 */
const protectedRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/views/layout/BasicLayout.vue'),
    redirect: '/dashboard',
    meta: {
      title: '首页',
      requiresAuth: true,
    },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: {
          title: '工作台',
          requiresAuth: true,
        },
      },
      {
        path: 'jobs',
        name: 'JobSquare',
        component: () => import('@/views/job/JobSquare.vue'),
        meta: {
          title: '岗位广场',
          requiresAuth: true,
        },
      },
      {
        path: 'assistant',
        name: 'Assistant',
        component: () => import('@/views/assistant/AssistantView.vue'),
        meta: {
          title: 'AI求职助手',
          requiresAuth: true,
        },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/ProfileView.vue'),
        meta: {
          title: '求职画像',
          requiresAuth: true,
        },
      },
      {
        path: 'resumes',
        name: 'Resume',
        component: () => import('@/views/resume/ResumeView.vue'),
        meta: {
          title: '简历管理',
          requiresAuth: true,
        },
      },
      {
        path: 'ability',
        name: 'Ability',
        component: () => import('@/views/ability/AbilityView.vue'),
        meta: {
          title: '能力画像',
          requiresAuth: true,
        },
      },
      {
        path: 'interviews',
        name: 'Interviews',
        component: () => import('@/views/interview/InterviewListView.vue'),
        meta: {
          title: '模拟面试',
          requiresAuth: true,
        },
      },
      {
        path: 'interviews/:id',
        name: 'InterviewSession',
        component: () => import('@/views/interview/InterviewSessionView.vue'),
        meta: {
          title: '面试进行中',
          requiresAuth: true,
        },
      },
      {
        path: 'interviews/:id/review',
        name: 'InterviewReview',
        component: () => import('@/views/interview/InterviewReviewView.vue'),
        meta: {
          title: '面试复盘',
          requiresAuth: true,
        },
      },
    ],
  },
]

/**
 * 兜底路由：未匹配路径重定向到首页
 */
const fallbackRoute: RouteRecordRaw = {
  path: '/:pathMatch(.*)*',
  redirect: '/',
}

/** 路由实例 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [...publicRoutes, ...protectedRoutes, fallbackRoute],
})

export default router
