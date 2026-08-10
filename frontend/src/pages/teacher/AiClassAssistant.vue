<template>
  <div class="assistant-page">
    <div class="assistant-header">
      <div>
        <h3>AI 班级分析助手</h3>
        <p>基于当前教师有权限访问的班级和学科，查询学情并生成教学建议。</p>
      </div>
      <div class="scope-selectors">
        <el-select v-model="selectedClass" placeholder="选择班级" clearable>
          <el-option
            v-for="item in classList"
            :key="item.class_id"
            :label="item.class_name"
            :value="item.class_id"
          />
        </el-select>
        <el-select v-model="selectedCourse" placeholder="选择学科" clearable>
          <el-option
            v-for="item in courseList"
            :key="item.course_id"
            :label="item.course_name"
            :value="item.course_id"
          />
        </el-select>
      </div>
    </div>

    <div v-if="!selectedClass || !selectedCourse" class="scope-warning">
      请先选择班级和学科，再向助手提问。
    </div>

    <div class="chat-container">
      <div class="chat-messages">
        <div v-if="messages.length === 0" class="empty-state">
          <el-icon :size="48" color="#94a3b8"><MessageCircle /></el-icon>
          <p>你可以询问：</p>
          <div class="suggestion-chips">
            <el-tag
              v-for="question in suggestions"
              :key="question"
              class="suggestion-chip"
              type="info"
              effect="plain"
              @click="sendSuggestion(question)"
            >
              {{ question }}
            </el-tag>
          </div>
        </div>
        <ChatMessage
          v-for="message in messages"
          :key="message.id"
          :message="message"
          :loading="loading && message.id === messages[messages.length - 1]?.id"
        />
      </div>
      <ChatInput :loading="loading" @send="sendScopedMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MessageCircle } from 'lucide-vue-next'
import ChatInput from '@/components/ChatInput.vue'
import ChatMessage from '@/components/ChatMessage.vue'
import { useChat } from '@/composables/useChat'
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

const { messages, loading, sendMessage } = useChat({
  getAgent: () => ({
    agentId: 'teacher.class_assistant',
    classId: selectedClass.value ?? undefined,
    courseId: selectedCourse.value ?? undefined,
  }),
})

const suggestions = [
  '班级平均掌握度最低的知识点有哪些？',
  '最近哪些学生需要重点关注？',
  '当前学科错误最多的知识点是什么？',
  '请给出本班下一阶段的教学建议。',
]

function sendScopedMessage(content: string) {
  if (!selectedClass.value || !selectedCourse.value) {
    ElMessage.warning('请先选择班级和学科')
    return
  }
  void sendMessage(content)
}

function sendSuggestion(content: string) {
  sendScopedMessage(content)
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
    console.error('加载班级助手范围失败:', error)
    ElMessage.error('班级和学科加载失败，请稍后重试')
  }
})
</script>

<style scoped>
.assistant-page { display: flex; flex-direction: column; height: calc(100vh - 48px); }
.assistant-header { display: flex; justify-content: space-between; gap: 20px; align-items: center; padding: 16px 20px; border-bottom: 1px solid rgba(0,0,0,0.06); background: rgba(255,255,255,0.6); backdrop-filter: blur(10px); }
.assistant-header h3 { margin: 0; font-size: 1.1rem; color: #1e293b; }
.assistant-header p { margin: 6px 0 0; font-size: 0.85rem; color: #64748b; }
.scope-selectors { display: flex; gap: 10px; min-width: 360px; }
.scope-selectors .el-select { flex: 1; }
.scope-warning { padding: 10px 20px; color: #b45309; background: #fffbeb; border-bottom: 1px solid #fde68a; font-size: 13px; }
.chat-container { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.chat-messages { flex: 1; overflow-y: auto; padding: 24px; }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 260px; color: #64748b; text-align: center; }
.empty-state p { margin: 14px 0; }
.suggestion-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; max-width: 760px; }
.suggestion-chip { cursor: pointer; }
@media (max-width: 760px) {
  .assistant-header { align-items: stretch; flex-direction: column; }
  .scope-selectors { min-width: 0; }
}
</style>
