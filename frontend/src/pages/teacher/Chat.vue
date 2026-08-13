<template>
  <div class="chat-page teacher-page">
    <div class="chat-toolbar">
      <div class="mode-tabs">
        <button v-for="item in navItems" :key="item.value" type="button" :class="{ active: chatMode === item.value }" @click="chatMode = item.value as any">{{ item.label }}</button>
      </div>
      <div class="header-actions">
        <div v-if="chatMode === 'agent'" class="scope-selectors">
          <el-select v-model="selectedClass" size="small" placeholder="选择班级" clearable>
            <el-option
              v-for="item in classList"
              :key="item.class_id"
              :label="item.class_name"
              :value="item.class_id"
            />
          </el-select>
          <el-select v-model="selectedCourse" size="small" placeholder="选择学科" clearable>
            <el-option
              v-for="item in courseList"
              :key="item.course_id"
              :label="item.course_name"
              :value="item.course_id"
            />
          </el-select>
        </div>
        <button class="clear-button" type="button" :disabled="messages.length === 0" @click="clearMessages">清空对话</button>
      </div>
    </div>

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

      <!-- 右侧对话主面板 -->
      <div class="messages-shell">
        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="empty-state">
            <div class="welcome-copy">
              <span class="welcome-icon"><Sparkles :size="20" /></span>
              <h2>你好，{{ userName }}</h2>
              <p>今天需要我协助完成什么教学工作？</p>
            </div>
            <div class="welcome-composer">
              <ChatInput prominent :loading="loading" placeholder="输入教学问题，或描述你希望准备的课程内容…" @send="handleSend" />
              <div class="prompt-chips">
                <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="handleSend(prompt)">{{ prompt }}</button>
              </div>
            </div>
            <div class="welcome-note"><BookOpenCheck :size="17" /><span>辅助备课模式可结合班级学情与课程知识生成教学建议</span></div>
          </div>
          <ChatMessage
            v-for="(msg, i) in messages"
            :key="i"
            :message="msg"
            :loading="loading && i === messages.length - 1"
          />
        </div>

        <div v-if="messages.length > 0" class="conversation-composer"><ChatInput :loading="loading" @send="handleSend" /></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { Sparkles, BookOpenCheck } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useChat } from '@/composables/useChat'
import { useAuthStore } from '@/stores/auth'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'
import AgentConversationSidebar from '@/components/AgentConversationSidebar.vue'
import {
  deleteAgentConversation,
  getAgentConversation,
  listAgentConversations,
  type AgentConversationSummary,
} from '@/api/ai'
import {
  getTeacherClasses,
  getTeacherCourses,
  type TeacherClass,
  type TeacherCourse,
} from '@/api/teacher'

const selectedClass = ref<number | null>(null)
const selectedCourse = ref<number | null>(null)
const classList = ref<TeacherClass[]>([])
const courseList = ref<TeacherCourse[]>([])
const authStore = useAuthStore()
const userName = computed(() => authStore.user?.name || '老师')
const quickPrompts = ['生成一份教案', '分析班级薄弱项', '设计课堂练习', '整理章节重点', '生成课后作业']

const {
  messages,
  loading,
  sendMessage,
  clearMessages,
  chatMode,
  activeConversationId,
  loadConversation,
} = useChat({
  getAgent: () => ({
    agentId: 'teacher.class_assistant',
    classId: selectedClass.value ?? undefined,
    courseId: selectedCourse.value ?? undefined,
  }),
})
const messagesRef = ref<HTMLElement>()
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
    console.error('加载教师 Agent 历史会话失败:', error)
  } finally {
    conversationsLoading.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  try {
    const conversation = await getAgentConversation(conversationId)
    loadConversation(conversation.messages, conversation.conversation_id)
  } catch (error) {
    console.error('恢复教师 Agent 会话失败:', error)
    ElMessage.error('历史会话加载失败，请稍后重试')
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
    console.error('删除教师 Agent 会话失败:', error)
    ElMessage.error('历史会话删除失败，请稍后重试')
  }
}

// 教师端模式配置：轻度思考、深度思考、辅助备课
const navItems = [
  { label: '轻度思考', value: 'quick' },
  { label: '深度思考', value: 'deep' },
  { label: '辅助备课', value: 'agent' }
]

function handleSend(content: string) {
  if (chatMode.value === 'agent' && (!selectedClass.value || !selectedCourse.value)) {
    ElMessage.warning('请先选择班级和学科，再使用辅助备课模式')
    return
  }
  void sendMessage(content)
}

onMounted(async () => {
  try {
    const [classes, courses] = await Promise.all([
      getTeacherClasses(),
      getTeacherCourses(),
    ])
    classList.value = classes
    courseList.value = courses
    selectedClass.value = classes[0]?.class_id ?? null
    selectedCourse.value = courses[0]?.course_id ?? null
  } catch (error) {
    console.error('加载教师 Agent 范围失败:', error)
    ElMessage.error('班级和学科加载失败，请稍后重试')
  }
  void refreshConversations()
})

watch(
  () => loading.value,
  (isLoading, wasLoading) => {
    if (wasLoading && !isLoading) void refreshConversations()
  },
)

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
  height: calc(100vh - 184px);
  min-height: 620px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e2e7ef;
  border-radius: 10px;
  background: #fff;
}
.chat-toolbar { min-height: 55px; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 9px 14px; border-bottom: 1px solid #e4e9f0; background: #fafbfc; }
.mode-tabs { display: flex; gap: 3px; padding: 3px; border: 1px solid #e2e7ef; border-radius: 8px; background: #eef1f5; }
.mode-tabs button { padding: 7px 12px; border: 0; border-radius: 6px; color: #667085; background: transparent; font-size: 12px; cursor: pointer; }
.mode-tabs button.active { color: #172033; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.05); font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.clear-button { height: 32px; padding: 0 10px; border: 1px solid #dfe5ed; border-radius: 7px; color: #667085; background: #fff; font-size: 12px; cursor: pointer; }
.clear-button:disabled { opacity: .4; cursor: not-allowed; }
.scope-selectors {
  display: flex;
  gap: 8px;
  align-items: center;
}
.scope-selectors :deep(.el-select) {
  width: 132px;
}
.chat-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.messages-shell { display: flex; position: relative; flex: 1; min-width: 0; flex-direction: column; }
.chat-messages { flex: 1; min-height: 0; overflow-y: auto; padding: 30px 38px; }
.empty-state { width: min(100%, 800px); min-height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: auto; }
.welcome-copy { text-align: center; }
.welcome-icon { width: 42px; height: 42px; display: grid; place-items: center; margin: 0 auto 16px; border: 1px solid #dbe3ef; border-radius: 10px; color: #21469b; background: #f1f4fa; }
.welcome-copy h2 { margin: 0; color: #101828; font-size: 34px; letter-spacing: -.035em; }
.welcome-copy p { margin: 9px 0 0; color: #7a8699; font-size: 14px; }
.welcome-composer { width: 100%; margin-top: 34px; }
.prompt-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }
.prompt-chips button { padding: 7px 12px; border: 1px solid #dfe5ed; border-radius: 18px; color: #526078; background: #fff; font-size: 12px; cursor: pointer; }
.prompt-chips button:hover { color: #21469b; border-color: #bac7dc; background: #f5f7fb; }
.welcome-note { display: flex; align-items: center; gap: 9px; margin-top: 36px; padding: 11px 14px; border: 1px solid #e2e7ef; border-radius: 8px; color: #667085; background: #fafbfc; font-size: 12px; }
.conversation-composer { width: min(880px, calc(100% - 56px)); margin: 0 auto; padding: 12px 0 18px; background: #fff; }

/* 自定义滚动条样式 */
.chat-messages::-webkit-scrollbar,
.history-panel .overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track,
.history-panel .overflow-y-auto::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb,
.history-panel .overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.history-panel .overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}
@media (max-width: 850px) {
  .chat-page { height: calc(100vh - 168px); min-height: 520px; }
  .chat-toolbar { align-items: flex-start; flex-direction: column; }
  .header-actions { width: 100%; flex-wrap: wrap; }
  .chat-messages { padding: 22px 16px; }
  .welcome-copy h2 { font-size: 27px; }
  .conversation-composer { width: calc(100% - 24px); }
}
</style>
