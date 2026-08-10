<template>
  <aside class="conversation-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <span v-if="!collapsed" class="sidebar-title">历史对话</span>
      <div class="sidebar-actions">
        <button v-if="!collapsed" class="new-button" type="button" @click="$emit('new')">
          新建
        </button>
        <button class="toggle-button" type="button" :aria-label="collapsed ? '展开历史对话' : '收起历史对话'" @click="$emit('toggle')">
          {{ collapsed ? '›' : '‹' }}
        </button>
      </div>
    </div>

    <div v-if="!collapsed" class="conversation-list">
      <div v-if="loading" class="list-placeholder">加载中...</div>
      <div v-else-if="conversations.length === 0" class="list-placeholder">
        暂无历史会话
      </div>
      <template v-else>
        <button
          v-for="conversation in conversations"
          :key="conversation.conversation_id"
          class="conversation-item"
          :class="{ active: conversation.conversation_id === activeId }"
          type="button"
          @click="$emit('select', conversation.conversation_id)"
        >
          <span class="conversation-copy">
            <span class="conversation-title">{{ conversation.title || '新对话' }}</span>
            <span class="conversation-meta">
              {{ formatDate(conversation.last_message_at) }} · {{ conversation.message_count }} 条消息
            </span>
          </span>
          <span
            class="delete-button"
            role="button"
            tabindex="0"
            aria-label="删除会话"
            @click.stop="$emit('delete', conversation.conversation_id)"
            @keydown.enter.stop="$emit('delete', conversation.conversation_id)"
          >
            ×
          </span>
        </button>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { AgentConversationSummary } from '@/api/ai'

defineProps<{
  conversations: AgentConversationSummary[]
  activeId?: string
  collapsed?: boolean
  loading?: boolean
}>()

defineEmits<{
  select: [conversationId: string]
  new: []
  delete: [conversationId: string]
  toggle: []
}>()

function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped>
.conversation-sidebar {
  width: 256px;
  flex: 0 0 256px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(10px);
  transition: width 0.2s ease, flex-basis 0.2s ease;
}

.conversation-sidebar.collapsed {
  width: 48px;
  flex-basis: 48px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 48px;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.sidebar-title {
  overflow: hidden;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.sidebar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.new-button,
.toggle-button,
.delete-button {
  border: 0;
  cursor: pointer;
}

.new-button {
  padding: 4px 8px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.12);
  color: #409eff;
  font-size: 12px;
}

.toggle-button {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  font-size: 22px;
  line-height: 24px;
}

.toggle-button:hover,
.new-button:hover {
  background: rgba(64, 158, 255, 0.18);
}

.conversation-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
}

.list-placeholder {
  padding: 20px 8px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}

.conversation-item {
  position: relative;
  display: flex;
  width: 100%;
  align-items: flex-start;
  gap: 6px;
  padding: 9px 8px;
  margin-bottom: 4px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  text-align: left;
}

.conversation-item:hover,
.conversation-item.active {
  border-color: rgba(64, 158, 255, 0.18);
  background: rgba(255, 255, 255, 0.72);
}

.conversation-copy {
  min-width: 0;
  flex: 1;
}

.conversation-title,
.conversation-meta {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-title {
  color: #334155;
  font-size: 12px;
}

.conversation-meta {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 10px;
}

.delete-button {
  flex: 0 0 auto;
  padding: 0 2px;
  color: #cbd5e1;
  font-size: 16px;
  line-height: 16px;
}

.delete-button:hover {
  color: #f56c6c;
}

@media (max-width: 720px) {
  .conversation-sidebar {
    width: 192px;
    flex-basis: 192px;
  }
}
</style>
