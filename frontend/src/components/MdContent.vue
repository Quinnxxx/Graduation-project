<script setup lang="ts">
/**
 * Markdown 渲染组件
 *
 * - 使用 markdown-it 解析 Markdown，highlight.js 做代码块高亮；
 * - html:false 为硬性安全要求：禁用原文中的原始 HTML，防止 XSS 注入；
 * - loading 为 true 时在文末追加闪烁光标，表达“正在生成”。
 *
 * 注意：渲染结果通过 v-html 注入，排版样式（.md-body 及其子元素、光标）
 * 统一写在全局 assets/styles/index.css 中（scoped 样式无法命中 v-html 注入节点）。
 */

import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = withDefaults(
  defineProps<{
    /** Markdown 文本 */
    content: string
    /** 是否正在加载（加载时文末显示闪烁光标） */
    loading?: boolean
  }>(),
  {
    content: '',
    loading: false,
  },
)

/**
 * markdown-it 实例
 *
 * highlight 约定：命中注册语言时用该语言高亮；未知语言走 highlightAuto；
 * 任一高亮过程异常时返回空串，由 markdown-it 回退为默认 HTML 转义。
 */
const md = new MarkdownIt({
  // 安全硬性要求：关闭原始 HTML，避免不可信内容注入
  html: false,
  linkify: true,
  breaks: false,
  highlight(str: string, lang: string): string {
    const language = lang?.trim()
    if (language && hljs.getLanguage(language)) {
      try {
        const highlighted = hljs.highlight(str, {
          language,
          ignoreIllegals: true,
        }).value
        return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
      } catch {
        // 落到自动识别
      }
    }
    try {
      return `<pre><code class="hljs">${hljs.highlightAuto(str).value}</code></pre>`
    } catch {
      // 高亮彻底失败：返回空串，交由 markdown-it 默认转义
      return ''
    }
  },
})

/** 渲染后的 HTML；loading 时在末尾拼接闪烁光标（光标为可信自生成节点） */
const html = computed<string>(() => {
  const rendered = md.render(props.content || '')
  return props.loading
    ? `${rendered}<span class="md-cursor" aria-hidden="true"></span>`
    : rendered
})
</script>

<template>
  <div class="md-body" v-html="html"></div>
</template>
