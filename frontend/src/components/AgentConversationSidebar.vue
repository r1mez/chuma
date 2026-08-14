<template>
  <aside class="conversation-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <div class="sidebar-actions">
        <button v-if="!collapsed" class="new-button" type="button" @click="$emit('new')">
          <Plus :size="14" />
          <span>新建对话</span>
        </button>
        <button class="toggle-button" type="button" :aria-label="collapsed ? '展开历史对话' : '收起历史对话'" @click="$emit('toggle')">
          <PanelLeftOpen v-if="collapsed" :size="16" />
          <PanelLeftClose v-else :size="16" />
        </button>
      </div>
    </div>

    <div v-if="!collapsed" class="conversation-list">
      <div v-if="loading" class="list-placeholder">加载中...</div>
      <div v-else-if="conversations.length === 0" class="list-placeholder">
        暂无历史会话
      </div>
      <template v-else>
        <div
          v-for="conversation in conversations"
          :key="conversation.conversation_id"
          class="conversation-row"
        >
          <button
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
          </button>
          <button
            class="delete-button"
            type="button"
            aria-label="删除会话"
            @click.stop="$emit('delete', conversation.conversation_id)"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { PanelLeftClose, PanelLeftOpen, Plus, Trash2 } from 'lucide-vue-next'
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
  border-right: 1px solid var(--workspace-border);
  background: #f4f7fb;
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
  min-height: 50px;
  padding: 8px 14px;
  background: #fff;
  border-bottom: 1px solid var(--workspace-border);
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  cursor: pointer;
}

.new-button {
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--workspace-primary);
  color: #fff;
  font-size: 12px;
  border: 1px solid var(--workspace-primary);
  box-shadow: 0 4px 10px rgba(33, 70, 155, .14);
  transition: background-color .18s ease, box-shadow .18s ease;
}

.toggle-button {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  transition: background-color .18s ease, color .18s ease;
}

.toggle-button:hover { color: var(--workspace-primary); background: var(--workspace-primary-soft); }
.new-button:hover { border-color: var(--workspace-primary-hover); background: var(--workspace-primary-hover); box-shadow: 0 5px 12px rgba(33, 70, 155, .18); }
.new-button:focus-visible,
.toggle-button:focus-visible,
.conversation-item:focus-visible { outline: 3px solid rgba(33, 70, 155, .16); outline-offset: 1px; }

.conversation-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 10px;
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
  gap: 8px;
  padding: 11px 10px;
  margin-bottom: 0;
  padding-right: 40px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  text-align: left;
}

.conversation-row { position: relative; margin-bottom: 5px; }
.conversation-item:hover { border-color: #dbe5f3; background: #eef3fa; }
.conversation-item.active { border-color: var(--workspace-primary-border); background: var(--workspace-primary-soft); box-shadow: inset 3px 0 0 var(--workspace-primary); }

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
  color: #344054;
  font-size: 12px;
  font-weight: 600;
}

.conversation-meta {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 10px;
}

.delete-button {
  position: absolute;
  top: 10px;
  right: 8px;
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  margin-top: -1px;
  border-radius: 6px;
  color: #cbd5e1;
  opacity: 0;
  transition: color .18s ease, background-color .18s ease, opacity .18s ease;
}

.conversation-row:hover .delete-button,
.conversation-row:focus-within .delete-button,
.delete-button:focus-visible { opacity: 1; }
.delete-button:hover,
.delete-button:focus-visible {
  color: var(--workspace-danger);
  background: #fff1f1;
}

@media (max-width: 720px) {
  .conversation-sidebar {
    width: 212px;
    flex-basis: 212px;
  }
}
</style>
