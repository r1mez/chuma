<template>
  <div class="chat-message" :class="message.role">
    <div class="avatar">
      <el-icon v-if="message.role === 'user'" :size="20"><User /></el-icon>
      <el-icon v-else :size="20"><Monitor /></el-icon>
    </div>
    <div class="bubble">
      <div v-if="loading && message.role === 'assistant' && !message.content && !message.reasoning" class="typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
      <div v-else>
        <!-- 思考过程（可折叠，仅深度思考模式有） -->
        <div v-if="message.reasoning" class="reasoning-section">
          <div class="reasoning-header" @click="toggleReasoning">
            <el-icon :size="14">
              <ArrowRight v-if="!showReasoning" />
              <ArrowDown v-else />
            </el-icon>
            <span>思考过程</span>
            <span v-if="isThinking" class="thinking-indicator">思考中...</span>
          </div>
          <div v-show="showReasoning" class="reasoning-content">
            <pre>{{ message.reasoning }}</pre>
          </div>
        </div>
        <!-- 正式回答 -->
        <div class="markdown-body" v-html="renderedContent"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { User, Monitor, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import katex from 'katex'
import type { ChatMessage } from '@/composables/useChat'

// 思考中自动展开，思考完毕自动收起；用户手动点击可覆盖
const showReasoning = ref(true)
const userToggled = ref(false)

const props = defineProps<{
  message: ChatMessage
  loading?: boolean
}>()

// 思考中 = loading 且有 reasoning 但还没有正式 content
const isThinking = computed(() =>
  props.loading && !!props.message.reasoning && !props.message.content
)

// 思考完毕 = 有 reasoning 且有 content（loading 可能还在）
const thinkingDone = computed(() =>
  !!props.message.reasoning && !!props.message.content
)

// 自动展开/收起逻辑
watch(isThinking, (val) => {
  if (val && !userToggled.value) {
    showReasoning.value = true
  }
})

watch(thinkingDone, (val) => {
  if (val && !userToggled.value) {
    showReasoning.value = false
  }
})

function toggleReasoning() {
  userToggled.value = true
  showReasoning.value = !showReasoning.value
}

// 创建带自定义渲染器的 marked 实例
const markedRenderer = new marked.Renderer()

// 配置 marked 使用 highlight.js（v14 使用扩展方式）
const markedWithHighlight = {
  ...marked,
  renderer: markedRenderer,
}

// 渲染 Markdown 内容
function renderMarkdown(content: string): string {
  const result = marked.parse(content, {
    breaks: true,
    gfm: true,
  })
  if (typeof result === 'string') {
    return result
  }
  return ''
}

// 渲染 LaTeX 公式
function renderMath(text: string): string {
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: true, throwOnError: false })
    } catch {
      return `$$${math}$$`
    }
  })
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, math) => {
    try {
      return katex.renderToString(math.trim(), { displayMode: false, throwOnError: false })
    } catch {
      return `$${math}$`
    }
  })
  return text
}

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  const html = renderMarkdown(props.message.content)
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

/* 思考过程区域 */
.reasoning-section {
  margin-bottom: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #fafafa;
}
.reasoning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}
.reasoning-header:hover {
  background: #f5f7fa;
  border-radius: 8px 8px 0 0;
}
.thinking-indicator {
  font-size: 12px;
  color: #c0c4cc;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.reasoning-content {
  padding: 0 12px 12px;
}
.reasoning-content pre {
  margin: 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
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
