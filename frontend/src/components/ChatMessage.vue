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
      <div v-else class="content" v-html="renderContent(message.content)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { User, Monitor } from '@element-plus/icons-vue'
import type { ChatMessage } from '@/composables/useChat'

defineProps<{
  message: ChatMessage
  loading?: boolean
}>()

function renderContent(text: string): string {
  return text.replace(/\n/g, '<br>')
}
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
</style>
