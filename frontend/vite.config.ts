import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * Vite 构建配置
 *
 * 开发环境代理：
 * - /api  -> http://localhost:8080（business-service），剥离 /api 前缀
 * - /agent -> http://localhost:8001（ai-agent-service），剥离 /agent 前缀
 */
export default defineConfig(() => {
  return {
    plugins: [vue()],

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },

    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8080',
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api/, ''),
        },
        '/agent': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/agent/, ''),
        },
      },
    },

    build: {
      outDir: 'dist',
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          // 第三方依赖按需分包，优化首屏加载
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            antd: ['ant-design-vue', '@ant-design/icons-vue'],
          },
        },
      },
    },
  }
})
