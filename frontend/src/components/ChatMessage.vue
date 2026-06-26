<template>
  <div class="chat-message" :class="message.role">
    <div class="avatar">
      <el-icon v-if="message.role === 'user'" :size="20"><User /></el-icon>
      <el-icon v-else :size="20"><Monitor /></el-icon>
    </div>
    <div class="bubble">
      <div v-if="loading && message.role === 'assistant' && !message.content" class="typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
      <div v-else class="markdown-body" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, Monitor } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import type { ChatMessage } from '@/composables/useChat'

// 配置 marked 使用 highlight.js
marked.setOptions({
  highlight(code: string, lang: string) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

// 渲染 LaTeX 公式
function renderMath(text: string): string {
  // 处理 $$...$$ 块级公式
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })
    } catch {
      return `$$${math}$$`
    }
  })
  // 处理 $...$ 行内公式
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })
    } catch {
      return `$${math}$`
    }
  })
  return text
}

const props = defineProps<{
  message: ChatMessage
  loading?: boolean
}>()

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  // 先渲染 Markdown，再渲染 LaTeX 公式
  const html = marked.parse(props.message.content)
  return renderMath(html)
})
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.chat-message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.chat-message.user .avatar {
  background: #409eff;
  color: white;
}
.chat-message.assistant .avatar {
  background: #e4e7ed;
  color: #606266;
}
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
}
.chat-message.user .bubble {
  background: #409eff;
  color: white;
  border-top-right-radius: 4px;
}
.chat-message.assistant .bubble {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}
.typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* Markdown 样式 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 12px 0 8px;
  font-weight: 600;
}
.markdown-body :deep(h1) { font-size: 1.4em; }
.markdown-body :deep(h2) { font-size: 1.2em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(code) {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 0.85em;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #409eff;
  padding-left: 12px;
  margin: 8px 0;
  color: #606266;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e4e7ed;
  margin: 12px 0;
}

/* KaTeX 公式样式 */
.markdown-body :deep(.katex) {
  font-size: 1em;
}
.markdown-body :deep(.katex-display) {
  margin: 8px 0;
  overflow-x: auto;
}
</style>
