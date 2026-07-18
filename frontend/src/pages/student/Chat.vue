<template>
  <div class="chat-page">
    <!-- 顶部栏 -->
    <div class="chat-header">
      <h3>AI 助教</h3>
      <div class="header-actions">
        <GooeyNav 
          :items="navItems"
          v-model="chatMode"
        />
        <StarBorder as="div" color="#f56c6c" speed="4s" class="clear-btn-wrapper">
          <el-button text @click="clearMessages" :disabled="messages.length === 0" class="clear-btn">
            清空对话
          </el-button>
        </StarBorder>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>开始向 AI 助教提问吧！</p>
        <p class="hint">支持 408 考研、数据库原理等计算机科学问题</p>
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :message="msg"
        :loading="loading && i === messages.length - 1"
      />
    </div>

    <!-- 输入框 -->
    <ChatInput :loading="loading" @send="sendMessage" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { useChat } from '@/composables/useChat'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import GooeyNav from '@/components/GooeyNav.vue'
import StarBorder from '@/components/StarBorder.vue'

const { messages, loading, sendMessage, clearMessages, chatMode } = useChat()
const messagesRef = ref<HTMLElement>()

const navItems = [
  { label: '快速回答', value: 'quick' },
  { label: '深度思考', value: 'deep' },
  { label: '🤖 智能管家', value: 'agent' },
  { label: '规划模式 (开发中)', value: 'plan', disabled: true }
]

// 自动滚动到底部
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
// 流式输出时也要滚动
watch(
  () => messages.value[messages.value.length - 1]?.content,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  color: #303133;
}
.chat-header h3 {
  margin: 0;
  font-size: 16px;
}
.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
.clear-btn {
  margin-left: 8px;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}
.empty-state p {
  margin: 8px 0 0;
  font-size: 14px;
}
.hint {
  font-size: 12px !important;
  color: #c0c4cc;
}
</style>
