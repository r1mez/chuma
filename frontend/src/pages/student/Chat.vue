<template>
  <div class="chat-page">
    <div class="chat-body">
      <AgentConversationSidebar
        :conversations="conversations"
        :active-id="activeConversationId"
        :collapsed="isHistoryCollapsed"
        :loading="conversationsLoading"
        @select="handleSelectConversation"
        @new="handleNewConversation"
        @delete="handleDeleteConversation"
        @toggle="isHistoryCollapsed = !isHistoryCollapsed"
      />
      <div class="messages-shell">
        <div class="chat-messages" ref="messagesRef" @scroll="handleMessagesScroll">
          <div v-if="messages.length === 0" class="empty-state">
            <div class="welcome-copy">
              <div class="welcome-title">
                <span class="welcome-icon"><Sparkles :size="22" /></span>
                <h2>你好，我是 AI 助学</h2>
              </div>
              <p>{{ userName }}，今天想一起学习什么？</p>
            </div>
            <div class="welcome-composer">
              <ChatInput prominent :loading="loading" placeholder="向 AI 助学提问" @send="handleSend" @cancel="cancelCurrentRun" />
              <div class="prompt-chips">
                <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="handleSend(prompt)">{{ prompt }}</button>
              </div>
            </div>
            <div class="welcome-note"><BookOpen :size="17" /><span>可结合知识图谱与学习记录，为你提供个性化辅导</span></div>
          </div>
          <ChatMessage
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
            :loading="loading && msg.id === lastMessageId"
            :suggesting="suggesting && msg.id === lastMessageId && msg.mode === 'agent'"
            @select-question="handleSelectQuestion"
          />
        </div>
        <transition name="jump">
          <button v-if="showJumpToLatest" class="jump-latest" type="button" @click="scrollToLatest(true)">
            返回最新
            <span aria-hidden="true">↓</span>
          </button>
        </transition>
        <div v-if="messages.length > 0" class="conversation-composer">
          <ChatInput :loading="loading" @send="handleSend" @cancel="cancelCurrentRun" />
          <button class="clear-link" type="button" @click="clearMessages">清空当前对话</button>
        </div>
      </div>

      <ChatSubgraphPanel
        :visible="subgraphPanelVisible"
        :hit-nodes="kgHitNodes"
        :active-index="activeKgHitIndex"
        :subgraphs="activeSubgraph"
        :loading="activeSubgraphLoading"
        :error="activeSubgraphError"
        @close="closeSubgraphPanel"
        @open="openSubgraphPanel"
        @select-page="selectKgHitPage"
        @retry="handleRetrySubgraph"
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, Sparkles } from 'lucide-vue-next'
import { useChat } from '@/composables/useChat'
import { useAuthStore } from '@/stores/auth'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import AgentConversationSidebar from '@/components/AgentConversationSidebar.vue'
import ChatSubgraphPanel from '@/components/ChatSubgraphPanel.vue'
import {
  deleteAgentConversation,
  getAgentConversation,
  listAgentConversations,
  type AgentConversationSummary,
  type SuggestedQuestion,
} from '@/api/ai'

const {
  messages,
  loading,
  sendMessage,
  cancelCurrentRun,
  clearMessages,
  kgHitNodes,
  activeKgHitIndex,
  subgraphPanelVisible,
  closeSubgraphPanel,
  openSubgraphPanel,
  selectKgHitPage,
  subgraphs,
  subgraphLoading,
  subgraphErrors,
  extractSubgraphs,
  suggesting,
  selectSuggestedQuestion,
  activeConversationId,
  loadConversation,
  kgGraphIds,
} = useChat()
const authStore = useAuthStore()
const route = useRoute()
const userName = computed(() => authStore.user?.name || '同学')
const quickPrompts = ['解释一个知识点', '分析我的薄弱项', '制定复习计划', '带我做一道题', '整理课程重点']

const messagesRef = ref<HTMLElement>()
const nearBottom = ref(true)
const showJumpToLatest = ref(false)
const lastMessageId = computed(() => messages.value[messages.value.length - 1]?.id)
const activeSubgraph = computed(() => subgraphs.value[activeKgHitIndex.value] ?? null)
const activeSubgraphLoading = computed(() => subgraphLoading.value[activeKgHitIndex.value] ?? false)
const activeSubgraphError = computed(() => subgraphErrors.value[activeKgHitIndex.value] ?? null)
const isHistoryCollapsed = ref(false)
const conversations = ref<AgentConversationSummary[]>([])
const conversationsLoading = ref(false)

async function refreshConversations() {
  conversationsLoading.value = true
  try {
    const nextConversations = await listAgentConversations()
    conversations.value = nextConversations
    if (
      messages.value.length === 0
      && nextConversations.some(item => item.conversation_id === activeConversationId.value)
    ) {
      const currentConversation = await getAgentConversation(activeConversationId.value)
      loadConversation(currentConversation.messages, currentConversation.conversation_id)
    }
  } catch (error) {
    console.error('加载学生 Agent 历史会话失败:', error)
  } finally {
    conversationsLoading.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  try {
    const conversation = await getAgentConversation(conversationId)
    loadConversation(conversation.messages, conversation.conversation_id)
  } catch (error) {
    console.error('恢复学生 Agent 会话失败:', error)
  }
}

function handleNewConversation() {
  clearMessages()
}

async function handleDeleteConversation(conversationId: string) {
  try {
    await deleteAgentConversation(conversationId)
    if (activeConversationId.value === conversationId) clearMessages()
    await refreshConversations()
  } catch (error) {
    console.error('删除学生 Agent 会话失败:', error)
  }
}

function handleSelectQuestion(question: SuggestedQuestion) {
  nearBottom.value = true
  showJumpToLatest.value = false
  selectSuggestedQuestion(question)
}

function handleSend(content: string) {
  nearBottom.value = true
  showJumpToLatest.value = false
  sendMessage(content)
  scrollToLatest(true)
}

function handleRetrySubgraph() {
  const hitNode = kgHitNodes.value[activeKgHitIndex.value]
  if (hitNode) extractSubgraphs(hitNode, activeKgHitIndex.value)
}

onMounted(async () => {
  const graphId = Number(route.query.kgGraphId)
  if (Number.isInteger(graphId) && graphId > 0) {
    kgGraphIds.value = [graphId]
  }

  await refreshConversations()
  const question = typeof route.query.question === 'string' ? route.query.question : ''
  if (question) {
    handleSend(question)
  }
})

watch(
  () => loading.value,
  (isLoading, wasLoading) => {
    if (wasLoading && !isLoading) void refreshConversations()
  },
)

function handleMessagesScroll() {
  const element = messagesRef.value
  if (!element) return
  const distanceToBottom = element.scrollHeight - element.scrollTop - element.clientHeight
  nearBottom.value = distanceToBottom < 96
  if (nearBottom.value) showJumpToLatest.value = false
}

async function scrollToLatest(force = false) {
  await nextTick()
  const element = messagesRef.value
  if (!element) return
  if (!force && !nearBottom.value) {
    showJumpToLatest.value = true
    return
  }
  element.scrollTo({ top: element.scrollHeight, behavior: force ? 'smooth' : 'auto' })
  nearBottom.value = true
  showJumpToLatest.value = false
}

watch(
  () => messages.value.length,
  () => scrollToLatest(),
)

watch(
  () => {
    const last = messages.value[messages.value.length - 1]
    return [
      last?.content.length || 0,
      last?.agentRun?.steps.length || 0,
      last?.agentRun?.steps.map(step => step.status).join(',') || '',
      last?.suggestedQuestions?.length || 0,
    ]
  },
  () => scrollToLatest(),
)
</script>

<style scoped>
.chat-page {
  position: relative;
  isolation: isolate;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: #fff;
}
.chat-page::before {
  position: absolute;
  inset: 0 0 auto;
  height: 2px;
  content: '';
  background: linear-gradient(90deg, var(--workspace-primary), var(--workspace-accent));
  z-index: 2;
  pointer-events: none;
}
.chat-body { display: flex; flex: 1; min-width: 0; min-height: 0; overflow: hidden; background: #fff; }
.messages-shell { position: relative; display: flex; flex: 1; min-width: 0; flex-direction: column; }
.chat-messages { flex: 1; min-height: 0; overflow-y: auto; padding: 30px clamp(18px, 4vw, 48px) 28px; box-sizing: border-box; background: #fff; scroll-behavior: smooth; }
.chat-messages::-webkit-scrollbar { width: 8px; }
.chat-messages::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.02); border-radius: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.15); border-radius: 4px; }
.chat-messages::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.25); }
.empty-state { width: min(100%, 760px); min-height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: auto; color: #6b7280; }
.welcome-copy { text-align: center; }
.welcome-title { display: flex; align-items: center; justify-content: center; gap: 12px; }
.welcome-icon { width: 36px; height: 36px; display: grid; place-items: center; border: 1px solid var(--workspace-primary-border); border-radius: 10px; color: var(--workspace-primary); background: var(--workspace-primary-soft); }
.welcome-copy h2 { margin: 0; color: var(--workspace-heading); font-size: clamp(27px, 3vw, 36px); font-weight: 600; letter-spacing: -.04em; }
.welcome-copy p { margin: 12px 0 0; color: var(--workspace-muted); font-size: 14px; }
.welcome-composer { width: min(100%, 760px); margin-top: 34px; }
.prompt-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }
.prompt-chips button { padding: 7px 12px; border: 1px solid #dfe5ed; border-radius: 18px; color: #526078; background: #fff; font-size: 12px; cursor: pointer; transition: color .18s ease, border-color .18s ease, background-color .18s ease; }
.prompt-chips button:hover { color: var(--workspace-primary); border-color: var(--workspace-primary-border); background: var(--workspace-primary-soft); }
.welcome-note { display: flex; align-items: center; gap: 9px; margin-top: 30px; padding: 10px 14px; border: 1px solid #d6eee9; border-radius: 8px; color: #52736d; background: #f2fbf8; font-size: 12px; }
.conversation-composer { position: relative; z-index: 3; flex: 0 0 auto; width: min(920px, calc(100% - 48px)); margin: 0 auto; padding: 12px 0 16px; background: #fff; }
.clear-link { position: absolute; right: 0; bottom: 1px; border: 0; color: #98a2b3; background: transparent; font-size: 10px; cursor: pointer; transition: color .18s ease; }
.clear-link:hover { color: var(--workspace-danger); }
.jump-latest {
  position: absolute;
  left: 50%;
  bottom: 126px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid #dbe3ec;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #475569;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  font-size: 12px;
}
.jump-enter-active, .jump-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.jump-enter-from, .jump-leave-to { opacity: 0; transform: translate(-50%, 8px); }
@media (max-width: 800px) {
  .chat-page { height: 100%; min-height: 0; }
  .chat-messages { padding: 22px 16px; }
  .welcome-copy h2 { font-size: 27px; }
  .conversation-composer { width: calc(100% - 24px); }
}
@media (max-width: 700px) {
  :deep(.conversation-sidebar:not(.collapsed)) { width: 48px; flex-basis: 48px; }
  :deep(.conversation-sidebar:not(.collapsed) .new-button),
  :deep(.conversation-sidebar:not(.collapsed) .conversation-list) { display: none; }
  :deep(.conversation-sidebar:not(.collapsed) .sidebar-header) { justify-content: center; padding-inline: 6px; }
  :deep(.conversation-sidebar:not(.collapsed) .sidebar-actions) { margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .chat-messages { scroll-behavior: auto; }
  .jump-enter-active, .jump-leave-active { transition: none; }
}
</style>
