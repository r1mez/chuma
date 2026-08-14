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
              <span class="welcome-icon"><Sparkles :size="20" /></span>
              <h2>你好，{{ userName }}</h2>
              <p>今天想一起学习什么？</p>
            </div>
            <div class="welcome-composer">
              <ChatInput prominent :loading="loading" placeholder="输入课程问题，或描述你遇到的学习困难…" @send="handleSend" @cancel="cancelCurrentRun" />
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
import { Sparkles, BookOpen } from 'lucide-vue-next'
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
  height: calc(100vh - 184px);
  min-height: 620px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e2e7ef;
  border-radius: 10px;
  background: #fff;
}
.chat-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.messages-shell { position: relative; display: flex; flex: 1; min-width: 0; flex-direction: column; }
.chat-messages { flex: 1; min-height: 0; overflow-y: auto; padding: 30px 38px; box-sizing: border-box; scroll-behavior: smooth; }
.chat-messages::-webkit-scrollbar { width: 8px; }
.chat-messages::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.02); border-radius: 4px; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.15); border-radius: 4px; }
.chat-messages::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.25); }
.empty-state { width: min(100%, 800px); min-height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: auto; color: #6b7280; }
.welcome-copy { text-align: center; }
.welcome-icon { width: 42px; height: 42px; display: grid; place-items: center; margin: 0 auto 16px; border: 1px solid #dbe3ef; border-radius: 10px; color: #21469b; background: #f1f4fa; }
.welcome-copy h2 { margin: 0; color: #101828; font-size: 34px; letter-spacing: -.035em; }
.welcome-copy p { margin: 9px 0 0; color: #7a8699; font-size: 14px; }
.welcome-composer { width: 100%; margin-top: 34px; }
.prompt-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }
.prompt-chips button { padding: 7px 12px; border: 1px solid #dfe5ed; border-radius: 18px; color: #526078; background: #fff; font-size: 12px; cursor: pointer; }
.prompt-chips button:hover { color: #21469b; border-color: #bac7dc; background: #f5f7fb; }
.welcome-note { display: flex; align-items: center; gap: 9px; margin-top: 36px; padding: 11px 14px; border: 1px solid #e2e7ef; border-radius: 8px; color: #667085; background: #fafbfc; font-size: 12px; }
.conversation-composer { position: relative; width: min(880px, calc(100% - 56px)); margin: 0 auto; padding: 12px 0 18px; background: #fff; }
.clear-link { position: absolute; right: 4px; bottom: 1px; border: 0; color: #98a2b3; background: transparent; font-size: 10px; cursor: pointer; }
.clear-link:hover { color: #d14343; }
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
  .chat-page { height: calc(100vh - 168px); min-height: 520px; }
  .chat-messages { padding: 22px 16px; }
  .welcome-copy h2 { font-size: 27px; }
  .conversation-composer { width: calc(100% - 24px); }
}
@media (prefers-reduced-motion: reduce) {
  .chat-messages { scroll-behavior: auto; }
  .jump-enter-active, .jump-leave-active { transition: none; }
}
</style>
