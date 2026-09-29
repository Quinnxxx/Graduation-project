/**
 * 路由守卫
 *
 * 全局前置守卫：校验登录态与访问权限。
 * - 已登录访问 /login -> 重定向首页
 * - 未登录访问受保护路由 -> 重定向登录页并携带 redirect 参数
 */

import router from '@/router'
import { useUserStore } from '@/store/modules/user'

/** 公开路径白名单（无需登录即可访问） */
const WHITE_LIST: string[] = ['/login']

/**
 * 全局前置守卫
 *
 * @param to 目标路由
 * @param from 来源路由
 */
router.beforeEach((to, _from) => {
  // 设置页面标题
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - 校园招聘AI平台` : '校园招聘AI平台'

  const userStore = useUserStore()

  // 已登录
  if (userStore.token) {
    // 已登录访问登录页 -> 重定向首页
    if (to.path === '/login') {
      return { path: '/' }
    }
    return true
  }

  // 未登录
  if (WHITE_LIST.includes(to.path)) {
    return true
  }

  // 未登录访问受保护路由 -> 跳转登录页，携带回跳地址
  return {
    path: '/login',
    query: { redirect: to.fullPath },
  }
})
