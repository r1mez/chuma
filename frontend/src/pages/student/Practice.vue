<template>
  <BorderGlow class="practice-page" background-color="transparent">
    <div class="practice-layout">
      <!-- 左侧面板：题目与答案 (同一个大框，内部独立滚动) -->
      <div class="left-panel glass-card">
        <!-- 上半部分：题目与答题区 -->
        <div class="section-container" v-if="currentQuestion">
          <div class="question-header">
            <h3 class="title-red">题目 ({{ cachedIdList.length > 0 ? cachedIndex + 1 : currentIndex + 1 }} / {{ cachedIdList.length > 0 ? cachedIdList.length : questions.length }})：</h3>
            <div class="question-actions">
              <el-button size="small" type="danger" plain @click="prevQuestion" :disabled="cachedIdList.length > 0 ? cachedIndex === 0 : currentIndex === 0">上一题</el-button>
              <el-button size="small" type="danger" plain @click="nextQuestion" :disabled="cachedIdList.length > 0 ? cachedIndex === cachedIdList.length - 1 : currentIndex === questions.length - 1">下一题</el-button>
              <el-button size="small" type="info" plain @click="goBack">返回上一级</el-button>
            </div>
          </div>
          <div class="scroll-area relative-area">
            <div class="stem-content">{{ currentQuestion.question_description }}</div>
            
            <div class="answer-area">
              <div class="flex justify-between items-center mb-3">
                <h4 class="title-red answer-title mb-0">答题区：</h4>
                <el-button 
                  type="danger" 
                  size="small" 
                  @click="submitAnswer" 
                  :disabled="isAnswerSubmitted || (!userAnswer && userAnswerArray.length === 0)"
                >
                  {{ isAnswerSubmitted ? '已提交' : '提交答案' }}
                </el-button>
              </div>
              
              <!-- 单选题 -->
              <div v-if="currentQuestion.question_type === 'single_choice' || currentQuestion.question_type === 'choice'">
                <el-radio-group v-model="userAnswer" class="custom-radio-group" :disabled="isAnswerSubmitted">
                  <el-radio v-for="opt in parsedOptions" :key="opt.label" :value="opt.label">
                    {{ opt.label }}. {{ opt.text }}
                  </el-radio>
                </el-radio-group>
              </div>
              
              <!-- 多选题 -->
              <div v-else-if="currentQuestion.question_type === 'multiple_choice'">
                <el-checkbox-group v-model="userAnswerArray" class="custom-checkbox-group" :disabled="isAnswerSubmitted">
                  <el-checkbox v-for="opt in parsedOptions" :key="opt.label" :value="opt.label">
                    {{ opt.label }}. {{ opt.text }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              
              <!-- 判断题 -->
              <div v-else-if="currentQuestion.question_type === 'true_false'">
                <el-radio-group v-model="userAnswer" :disabled="isAnswerSubmitted">
                  <el-radio value="true">正确</el-radio>
                  <el-radio value="false">错误</el-radio>
                </el-radio-group>
              </div>
              
              <!-- 填空/解答题 -->
              <div v-else>
                <el-input
                  v-model="userAnswer"
                  type="textarea"
                  :rows="4"
                  placeholder="请在此输入你的答案（解答题留白区）..."
                  resize="none"
                  :disabled="isAnswerSubmitted"
                />
              </div>
            </div>
            <!-- 占位，确保底部不被遮挡 -->
            <div class="spacer"></div>
          </div>
        </div>
        
        <!-- 暂无题目 -->
        <div class="section-container" v-else-if="!loading">
           <div class="question-header">
            <h3 class="title-red">暂无题目</h3>
            <div class="question-actions">
              <el-button size="small" type="info" plain @click="goBack">返回上一级</el-button>
            </div>
          </div>
        </div>

        <!-- 红色分割线 -->
        <div class="divider" v-if="currentQuestion"></div>

        <!-- 下半部分：答案与解释 -->
        <div class="section-container" v-if="currentQuestion">
          <h3 class="title-red">答案与解释</h3>
          <div class="scroll-area">
            <div class="explanation-content" v-if="isAnswerSubmitted">
              <p><strong>正确答案：</strong> {{ currentQuestion.question_answer }}</p>
              <p class="mt-2" v-if="currentQuestion.question_explanation">{{ currentQuestion.question_explanation }}</p>
            </div>
            <div class="unsubmitted-notice" v-else>
              <el-icon class="mr-2"><Warning /></el-icon>
              <span>需要作答后方可查看答案与解析</span>
            </div>
            <div class="spacer"></div>
          </div>
        </div>
      </div>

        <!-- 右侧面板 -->
      <div class="right-panel">
        <!-- 上半部分：AI 分析与解惑 -->
        <div class="glass-card flex-card">
          <h3 class="title-blue">ai分析与解惑</h3>
          <div class="scroll-area">
            <div class="ai-content" v-if="showAiAnalysis">
              （AI 题目解析功能尚未实现，暂时留白）
            </div>
            <div class="flex items-center justify-center h-full" v-else>
              <el-button type="primary" plain @click="triggerAiAnalysis" :disabled="!isAnswerSubmitted">
                {{ isAnswerSubmitted ? '获取 AI 分析' : '请先提交答案' }}
              </el-button>
            </div>
            <div class="spacer"></div>
          </div>
        </div>

        <!-- 下半部分：同类型题型列举 -->
        <div class="glass-card flex-card">
          <h3 class="title-green">同类型题型列举</h3>
          <div class="scroll-area">
            <div v-if="showSimilarQuestions">
              <ul class="similar-list" v-if="similarQuestions.length > 0">
                <li v-for="sim in similarQuestions" :key="sim.id" class="similar-item">
                  <span class="dot"></span>
                  <span class="text">{{ sim.title }}</span>
                  <el-button size="small" type="success" plain class="go-btn">去练习</el-button>
                </li>
              </ul>
              <div v-else style="font-size: 0.9rem; color: #7f8c8d; margin-top: 8px;">
                （同类题型推荐功能尚未实现，暂时留白）
              </div>
            </div>
            <div class="flex items-center justify-center h-full" v-else>
              <el-button type="success" plain @click="triggerSimilarQuestions" :disabled="!isAnswerSubmitted">
                {{ isAnswerSubmitted ? '举一反三' : '请先提交答案' }}
              </el-button>
            </div>
            <div class="spacer"></div>
          </div>
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BorderGlow from '@/components/BorderGlow.vue'
import { fetchQuestions, fetchQuestionById, submitExerciseRecord, type Question } from '@/api/practice'

const route = useRoute()
const router = useRouter()

const questions = ref<Question[]>([])
const currentIndex = ref(0)
const loading = ref(true)
const isAnswerSubmitted = ref(false)
const showAiAnalysis = ref(false)
const showSimilarQuestions = ref(false)

// 全量 ID 数组缓存（用于仪表盘跳转后的前后切换）
const cachedIdList = ref<number[]>([])
const cachedIndex = ref(0)

const currentQuestion = computed(() => {
  return questions.value[currentIndex.value] || null
})

// Mock AI 分析与解惑 (由于后端未实现，暂时留白)
const aiAnalysis = ref('（AI 题目解析功能尚未实现，暂时留白）')
const similarQuestions = ref<any[]>([])

const userAnswer = ref('')
const userAnswerArray = ref([])

onMounted(async () => {
  const courseIdStr = route.query.module as string
  const questionIdStr = route.query.questionId as string
  const idListStr = route.query.idList as string
  const randomIndexStr = route.query.randomIndex as string
  const courseId = courseIdStr ? parseInt(courseIdStr, 10) : undefined
  const questionId = questionIdStr ? parseInt(questionIdStr, 10) : undefined

  if (!courseId && !questionId) {
    ElMessage.warning('未选择学科或题目')
    loading.value = false
    return
  }

  try {
    if (idListStr) {
      // 从仪表盘跳转：携带了全量 ID 列表和随机索引（全量 ID 数组缓存法）
      const idList = idListStr.split(',').map(Number).filter(id => !isNaN(id))
      const randomIndex = randomIndexStr ? parseInt(randomIndexStr, 10) : 0

      if (idList.length === 0) {
        ElMessage.error('题目列表参数无效')
        loading.value = false
        return
      }

      // 只加载当前索引对应的题目（按需加载，而非全量加载）
      const targetId = idList[randomIndex]
      if (!targetId) {
        ElMessage.error('目标题目索引无效')
        loading.value = false
        return
      }

      const question = await fetchQuestionById(targetId)
      if (question) {
        questions.value = [question]
        currentIndex.value = 0
        // 保存 ID 列表和当前索引到组件状态，供前后切换使用
        cachedIdList.value = idList
        cachedIndex.value = randomIndex
      } else {
        ElMessage.error('未找到该题目')
      }
    } else if (questionId) {
      // 通过 questionId 加载指定题目（从做题记录双击跳转）
      const question = await fetchQuestionById(questionId)
      if (question) {
        questions.value = [question]
        currentIndex.value = 0
      } else {
        ElMessage.error('未找到该题目')
      }
    } else if (courseId) {
      // 通过 courseId 加载该学科下所有题目（正常进入练习）
      const data = await fetchQuestions(courseId)
      questions.value = data || []
    }
  } catch (error) {
    console.error('Failed to fetch questions:', error)
    ElMessage.error('获取题目失败')
  } finally {
    loading.value = false
  }
})

// 题目切换逻辑
const prevQuestion = async () => {
  if (cachedIdList.value.length > 0) {
    // 全量 ID 缓存模式：通过索引切换
    if (cachedIndex.value > 0) {
      cachedIndex.value--
      await loadQuestionByCachedIndex()
    } else {
      ElMessage.warning('已经是第一题了')
    }
  } else if (currentIndex.value > 0) {
    currentIndex.value--
    resetAnswer()
    ElMessage.success('已切换至上一题')
  } else {
    ElMessage.warning('已经是第一题了')
  }
}

const nextQuestion = async () => {
  if (cachedIdList.value.length > 0) {
    // 全量 ID 缓存模式：通过索引切换
    if (cachedIndex.value < cachedIdList.value.length - 1) {
      cachedIndex.value++
      await loadQuestionByCachedIndex()
    } else {
      ElMessage.warning('已经是最后一题了')
    }
  } else if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
    resetAnswer()
    ElMessage.success('已切换至下一题')
  } else {
    ElMessage.warning('已经是最后一题了')
  }
}

/** 根据 cachedIndex 从 cachedIdList 中加载对应题目 */
const loadQuestionByCachedIndex = async () => {
  const targetId = cachedIdList.value[cachedIndex.value]
  if (!targetId) return
  try {
    const question = await fetchQuestionById(targetId)
    if (question) {
      questions.value = [question]
      currentIndex.value = 0
      resetAnswer()
      ElMessage.success(`已切换至第 ${cachedIndex.value + 1} 题`)
    }
  } catch (error) {
    console.error('切换题目失败:', error)
    ElMessage.error('切换题目失败')
  }
}

const submitAnswer = async () => {
  if (!currentQuestion.value) return

  // 构造学生答案字符串
  const answerStr = userAnswerArray.value.length > 0
    ? userAnswerArray.value.sort().join(',')
    : userAnswer.value

  try {
    await submitExerciseRecord({
      question_id: currentQuestion.value.question_id,
      course_id: currentQuestion.value.course_id,
      kg_node_name: currentQuestion.value.kg_node_name || undefined,
      question_type: currentQuestion.value.question_type,
      question_difficulty: currentQuestion.value.question_difficulty,
      do_stu_answer: answerStr,
    })
    isAnswerSubmitted.value = true
    ElMessage.success('答案已提交')
  } catch (error) {
    console.error('提交答案失败:', error)
    ElMessage.error('提交答案失败，请重试')
  }
}

const triggerAiAnalysis = () => {
  showAiAnalysis.value = true
}

const triggerSimilarQuestions = () => {
  showSimilarQuestions.value = true
}

const resetAnswer = () => {
  userAnswer.value = ''
  userAnswerArray.value = []
  isAnswerSubmitted.value = false
  showAiAnalysis.value = false
  showSimilarQuestions.value = false
}

const goBack = () => {
  router.back()
}

// 解析选项
const parsedOptions = computed(() => {
  if (!currentQuestion.value || !currentQuestion.value.question_options) return []
  const opts = currentQuestion.value.question_options
  // 假设后端返回的 json 是 { "A": "选项A内容", "B": "选项B内容" } 或者数组
  if (Array.isArray(opts)) {
    if (opts.length > 0 && typeof opts[0] === 'string') {
      const labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
      return opts.map((text, index) => ({
        label: labels[index] || String(index),
        text: text
      }))
    }
    return opts
  } else if (typeof opts === 'object') {
    return Object.entries(opts).map(([key, value]) => ({ label: key, text: value }))
  }
  return []
})
</script>

<style scoped>
.practice-page {
  color: #000;
  height: calc(100vh - 170px); /* 严格限制高度，防止页面拓展出全局滚动条 */
  margin: 20px;
}

.practice-layout {
  display: flex;
  gap: 24px;
  height: 100%;
  padding: 20px;
}

/* --- 玻璃拟态卡片基础样式 --- */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* --- 左侧面板 --- */
.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 保证内部滚动，外部不溢出 */
}

.section-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 限制高度，让内部 scroll-area 滚动 */
  padding: 20px;
}

.divider {
  height: 1px;
  background: #e74c3c; /* 按照线框图，使用红色分割线 */
  margin: 0 20px;
  flex-shrink: 0;
  opacity: 0.5;
}

/* --- 右侧面板 --- */
.right-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow: hidden;
}

.flex-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
}

/* --- 标题颜色匹配线框图 --- */
h3 {
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  flex-shrink: 0; /* 防止标题被挤压 */
}

.title-red {
  color: #c0392b;
}

.title-blue {
  color: #2980b9;
}

.title-green {
  color: #27ae60;
}

/* --- 题干头部样式 --- */
.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.question-header h3 {
  margin-bottom: 0;
}

.question-actions {
  display: flex;
  gap: 12px;
}

/* --- 滚动区域通用样式 (完全独立，互不影响) --- */
.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

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

/* --- 内容区细节样式 --- */
.stem-content {
  font-size: 1rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.answer-area {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #c0c5bd;
}

.answer-title {
  margin: 0 0 12px 0;
  font-size: 1rem;
  font-weight: 600;
}

.custom-radio-group,
.custom-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.explanation-content,
.ai-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.mock-text {
  margin-top: 16px;
  font-size: 0.85rem;
  color: #7f8c8d;
  line-height: 1.5;
}

.unsubmitted-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(243, 156, 18, 0.1);
  color: #d35400;
  border-radius: 8px;
  font-size: 0.95rem;
  margin-top: 16px;
}

/* --- 相似题目列表 --- */
.similar-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.similar-item {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  border-radius: 8px;
}

.similar-item .dot {
  width: 6px;
  height: 6px;
  background: #27ae60;
  border-radius: 50%;
  margin-right: 12px;
  flex-shrink: 0;
}

.similar-item .text {
  flex: 1;
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.go-btn {
  margin-left: 12px;
}

.mock-item {
  opacity: 0.5;
}
</style>
