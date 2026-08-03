<template>
  <div class="teacher-page h-full flex flex-col gap-6 p-4">
    <!-- 上半部分：互动列表 -->
    <el-card class="h-1/2 flex flex-col" shadow="never">
      <template #header>
        <span class="font-bold text-gray-800 text-sm">互动答疑</span>
        <span class="text-xs text-gray-500 ml-4">双击跳转详细对话面板</span>
      </template>
      <div class="h-full flex flex-col">
        <el-table
          :data="messageList"
          style="width: 100%; background: transparent;"
          class="flex-1"
          @row-dblclick="handleRowDblclick"
        >
          <el-table-column prop="stu_name" label="学生" width="120" />
          <el-table-column prop="msg_texts" label="问题、对话、描述等" min-width="300">
            <template #default="scope">
              <span class="truncate">{{ scope.row.msg_texts }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="answer_num" label="回答数" width="120">
            <template #default="scope">
              回答数 × {{ scope.row.answer_num }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="170" align="right">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
        <div class="mt-4 flex justify-center">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadMessages"
          />
        </div>
      </div>
    </el-card>

    <!-- 下半部分：作业/考试推送 -->
    <el-card class="h-1/2 flex flex-col" shadow="never">
      <template #header>
        <span class="font-bold text-gray-800 text-sm">作业 / 考试推送</span>
      </template>
      <div class="h-full flex gap-6">
        <!-- 操作区 -->
        <div class="w-48 flex flex-col gap-4">
          <div class="text-sm text-gray-600 mb-2">配置生成条件：</div>
          <el-select v-model="targetClass" placeholder="选择推送班级" size="small">
            <el-option label="2026级 计科1班" value="class1" />
            <el-option label="2026级 软件2班" value="class2" />
          </el-select>
          <el-select v-model="targetChapter" placeholder="选择章节范围" size="small">
            <el-option label="数据结构 - 图" value="ch1" />
            <el-option label="计算机组成 - CPU" value="ch2" />
          </el-select>
          <el-button type="primary" @click="generateContent" :loading="isGenerating" class="mt-auto">
            点击生成
          </el-button>
        </div>
        <!-- 内容展示区 -->
        <div class="flex-1 border border-gray-200 rounded-lg bg-gray-50/50 p-4 overflow-y-auto custom-scrollbar relative">
          <div v-if="!generatedContent" class="h-full flex items-center justify-center text-gray-400 text-sm">
            Agent 生成作业 / 考试内容展示区
          </div>
          <div v-else class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {{ generatedContent }}
          </div>
        </div>
      </div>
    </el-card>

    <!-- 详情对话框（微信聊天风格） -->
    <el-dialog
      v-model="detailDialogVisible"
      title="详细对话面板"
      width="70%"
      destroy-on-close
      @opened="scrollToBottom"
    >
      <div class="flex flex-col h-[500px] border border-gray-200 rounded-lg overflow-hidden">
        <!-- 问题区（置顶） -->
        <div class="p-4 border-b border-gray-200 bg-gray-50 shrink-0">
          <div class="font-bold text-sm text-gray-800 mb-2">问题区:</div>
          <div class="text-sm text-gray-700">
            <span class="font-bold mr-2">{{ currentDetail?.stu_name || '学生' }}:</span>
            {{ currentDetail?.msg_texts }}
          </div>
        </div>
        <!-- 答疑区（微信聊天风格，按时间正序：旧在上、新在下） -->
        <div ref="chatScrollRef" class="flex-1 p-4 overflow-y-auto custom-scrollbar bg-white">
          <div class="font-bold text-sm text-gray-800 mb-4">答疑区:</div>

          <div v-if="answers.length === 0" class="text-center text-gray-400 text-sm py-8">
            暂无回答，快来抢答吧~
          </div>

          <div
            v-for="answer in answers"
            :key="answer.answer_id"
            class="mb-4"
            :class="isMyAnswer(answer) ? 'text-right' : ''"
          >
            <div class="text-xs text-gray-500 mb-1">
              {{ answer.author_name || '匿名' }}
              <span v-if="answer.author_type === 'teacher'" class="ml-1 text-blue-500">(老师)</span>
              <span v-else class="ml-1 text-green-600">(学生)</span>
              <span class="ml-2">{{ formatTime(answer.created_at) }}</span>
            </div>
            <div
              class="p-3 rounded-lg text-sm text-gray-700 inline-block max-w-[80%] text-left break-words"
              :class="isMyAnswer(answer) ? 'bg-blue-50' : 'bg-gray-100'"
            >
              {{ answer.answer_text }}
            </div>
          </div>
        </div>
        <!-- 底部回复输入 -->
        <div class="p-4 border-t border-gray-200 bg-gray-50 flex gap-4 shrink-0">
          <el-input
            v-model="replyText"
            placeholder="输入回复内容..."
            class="flex-1"
            maxlength="500"
            @keyup.enter="handleReply"
          />
          <el-button type="primary" :loading="replying" @click="handleReply">回复</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchMessages,
  fetchAnswers,
  publishAnswer,
  type InteractionMessage,
  type InteractionAnswer
} from '@/api/interaction'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const messageList = ref<InteractionMessage[]>([])
const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(0)

/** 将时间格式化为 YYYY-MM-DD HH:mm:ss */
const formatTime = (value: string | null | undefined): string => {
  if (!value) return ''
  const date = new Date(value)
  if (isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

const loadMessages = async () => {
  try {
    const data = await fetchMessages(currentPage.value, pageSize.value)
    messageList.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error('加载互动消息失败')
  }
}

const detailDialogVisible = ref(false)
const currentDetail = ref<InteractionMessage | null>(null)
const answers = ref<InteractionAnswer[]>([])
const replyText = ref('')
const replying = ref(false)
const chatScrollRef = ref<HTMLElement | null>(null)

/** 判断某条回答是否为当前登录老师本人发布 */
const isMyAnswer = (answer: InteractionAnswer): boolean => {
  return answer.author_type === 'teacher' && answer.tea_id === authStore.user?.id
}

const handleRowDblclick = async (row: InteractionMessage) => {
  currentDetail.value = row
  answers.value = []
  replyText.value = ''
  detailDialogVisible.value = true
  try {
    answers.value = await fetchAnswers(row.msg_id)
    await nextTick()
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载回答失败')
  }
}

/** 滚动到底部（最新消息在下方） */
const scrollToBottom = () => {
  if (chatScrollRef.value) {
    chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
  }
}

const handleReply = async () => {
  const text = replyText.value.trim()
  if (!text) {
    ElMessage.warning('请输入回复内容')
    return
  }
  if (!currentDetail.value) return
  replying.value = true
  try {
    await publishAnswer(currentDetail.value.msg_id, text)
    ElMessage.success('回复成功')
    replyText.value = ''
    answers.value = await fetchAnswers(currentDetail.value.msg_id)
    // 同步刷新列表中的回答数
    await loadMessages()
    await nextTick()
    scrollToBottom()
  } catch (e) {
    ElMessage.error('回复失败')
  } finally {
    replying.value = false
  }
}

// 生成作业逻辑
const targetClass = ref('')
const targetChapter = ref('')
const isGenerating = ref(false)
const generatedContent = ref('')

const generateContent = () => {
  isGenerating.value = true
  setTimeout(() => {
    generatedContent.value = `基于 Agent 生成的作业/考试内容：\n\n一、 选择题\n1. 在一棵度为3的树中，度为3的节点有2个，度为2的节点有1个，度为1的节点有2个，则叶子节点有()个。\n   A. 4\n   B. 5\n   C. 6\n   D. 7\n\n二、 简答题\n1. 请简述图的深度优先搜索(DFS)和广度优先搜索(BFS)的区别与应用场景。\n\n...\n[更多内容由AI自动生成]`
    isGenerating.value = false
  }, 1500)
}

onMounted(() => {
  loadMessages()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

:deep(.el-table tr) {
  cursor: pointer;
}
</style>
