/**
 * 应用入口
 *
 * 按序注册：Pinia -> Router -> Ant Design Vue -> 全局样式
 * 路由守卫通过 import './router/guard' 副作用注册
 */

import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import router from './router'
import './router/guard'
import pinia from './store'

import './assets/styles/index.css'

/** 应用实例 */
const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(Antd)

app.mount('#app')
