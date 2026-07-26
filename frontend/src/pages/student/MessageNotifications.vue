<template>
  <BorderGlow class="messages-page" background-color="transparent">
    <div class="glass-card page-container">
      <h2 class="page-title">消息提醒</h2>
      
      <!-- 列表区域，独立滚动 -->
      <div class="list-container scroll-area">
        <div class="message-list">
          <div v-for="msg in mockMessages" :key="msg.id" class="message-item">
            <div class="msg-sender">{{ msg.sender }}:</div>
            <div class="msg-content">{{ msg.content }}</div>
            <div class="msg-time">{{ msg.time }}</div>
          </div>
        </div>
        <div class="spacer"></div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BorderGlow from '@/components/BorderGlow.vue'

// 模拟数据
const mockMessages = ref(
  Array.from({ length: 30 }).map((_, index) => {
    const senders = ['消息A', '消息B', '消息C']
    return {
      id: index + 1,
      sender: senders[index % 3],
      content: `占位 占位 占位 占位 占位 占位 占位 占位。。。。`,
      time: '2026-07-20 10:00'
    }
  })
)
</script>

<style scoped>
.messages-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #e5e8e4;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.page-title {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  font-weight: bold;
  color: #000;
  flex-shrink: 0;
}

.list-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scroll-area {
  overflow-y: auto;
  padding-right: 8px;
}

/* 自定义滚动条 */
.scroll-area::-webkit-scrollbar {
  width: 6px;
}
.scroll-area::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}
.scroll-area::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.spacer {
  height: 16px;
}

/* 消息列表样式 */
.message-list {
  display: flex;
  flex-direction: column;
}

.message-item {
  display: flex;
  align-items: center;
  padding: 16px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  transition: background-color 0.2s;
  cursor: pointer;
}

.message-item:hover {
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 8px;
}

.message-item:last-child {
  border-bottom: none;
}

.msg-sender {
  font-weight: bold;
  width: 80px;
  flex-shrink: 0;
}

.msg-content {
  flex: 1;
  margin: 0 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #333;
}

.msg-time {
  width: 140px;
  text-align: right;
  color: #666;
  font-size: 0.9rem;
  flex-shrink: 0;
}
</style>