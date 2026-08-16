<template>
  <BorderGlow class="practice-page" background-color="transparent">
    <div class="practice-layout">
      <div v-if="currentQuestion" class="practice-toolbar">
        <div class="practice-toolbar-context">
          <span class="section-eyebrow">练习进度</span>
          <strong>{{ currentQuestionNumber }} / {{ totalQuestions }}</strong>
          <el-tag v-if="practiceNodeName" size="small" type="info" effect="plain">
            {{ practiceNodeName }}
          </el-tag>
        </div>
        <div class="practice-progress" aria-hidden="true">
          <span :style="{ width: `${questionProgress}%` }"></span>
        </div>
        <div class="question-actions">
          <el-button size="small" plain @click="prevQuestion" :disabled="cachedIdList.length > 0 ? cachedIndex === 0 : currentIndex === 0">上一题</el-button>
          <el-button size="small" type="primary" plain @click="nextQuestion" :disabled="cachedIdList.length > 0 ? cachedIndex === cachedIdList.length - 1 : currentIndex === questions.length - 1">下一题</el-button>
          <el-button size="small" text @click="goBack">返回</el-button>
        </div>
      </div>

      <div class="practice-workspace">
      <!-- 左侧面板：题目与答案 (同一个大框，内部独立滚动) -->
      <main class="left-panel question-panel">
        <!-- 上半部分：题目与答题区 -->
        <div class="section-container" v-if="currentQuestion">
          <div class="question-intro">
            <span class="section-eyebrow">当前题目</span>
            <h2 class="question-title">请完成下面的题目</h2>
          </div>
          <div class="scroll-area relative-area">
            <div class="stem-content">{{ currentQuestion.question_description }}</div>
            
            <div class="answer-area">
              <div class="flex justify-between items-center mb-3">
                <h4 class="answer-title mb-0">答题区</h4>
                <el-button 
                  type="primary"
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
                <el-radio-group v-model="userAnswer" class="custom-radio-group" :disabled="isAnswerSubmitted">
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

            <div class="socratic-help-panel">
              <div class="socratic-help-header">
                <div>
                  <div class="socratic-help-title">苏格拉底式 AI 求助</div>
                  <div class="socratic-help-status">{{ hintStatusText }}</div>
                </div>
                <el-tag
                  size="small"
                  effect="plain"
                  :type="hintUnlocked ? 'success' : 'info'"
                >
                  {{ hintUnlocked ? '已解锁' : `${elapsedSeconds}s / 60s` }}
                </el-tag>
              </div>
              <p class="socratic-help-description">
                AI 只会通过问题引导你的思路，不会直接公布答案；每道题最多提供 3 级提示。
              </p>
              <div v-if="hintHistory.length > 0" class="socratic-hint-list">
                <div v-for="hint in hintHistory" :key="hint.hint_level" class="socratic-hint-item">
                  <el-tag size="small" type="warning" effect="plain">提示 {{ hint.hint_level }}</el-tag>
                  <span>{{ hint.content }}</span>
                </div>
              </div>
              <div class="socratic-help-actions">
                <el-button
                  type="primary"
                  plain
                  size="small"
                  :loading="hintLoading"
                  :disabled="!canRequestHint"
                  @click="requestSocraticHint"
                >
                  {{ hintButtonText }}
                </el-button>
                <span class="socratic-help-limit">已使用 {{ hintHistory.length }} / 3 级</span>
              </div>
            </div>
            <!-- 占位，确保底部不被遮挡 -->
            <div class="spacer"></div>
          </div>
        </div>
        
        <!-- 暂无题目 -->
        <div class="section-container" v-else-if="!loading">
           <div class="question-header">
            <h3 class="title-red">{{ emptyQuestionMessage }}</h3>
            <div class="question-actions">
              <el-button size="small" type="info" plain @click="goBack">返回上一级</el-button>
            </div>
          </div>
        </div>

        <!-- 提交后的答案与解释 -->
        <div class="review-section" v-if="currentQuestion">
          <div class="review-heading">
            <div>
              <span class="section-eyebrow">提交后查看</span>
              <h3 class="review-title">答案与解析</h3>
            </div>
            <el-tag v-if="isAnswerSubmitted" size="small" type="success" effect="plain">已完成</el-tag>
          </div>
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
      </main>

        <!-- 辅助栏：将 AI 分析与同类题收纳到同一工作区 -->
      <aside v-if="currentQuestion" class="practice-sidebar">
        <section class="session-card">
          <div class="session-card-heading">
            <div>
              <span class="section-eyebrow">本题信息</span>
              <h2>学习状态</h2>
            </div>
            <span class="session-count">{{ currentQuestionNumber }}/{{ totalQuestions }}</span>
          </div>
          <div class="session-row">
            <span>知识点</span>
            <strong>{{ practiceNodeName || currentQuestion.kg_node_name || '综合练习' }}</strong>
          </div>
          <div class="session-row">
            <span>作答状态</span>
            <strong :class="isAnswerSubmitted ? 'is-success' : 'is-pending'">
              {{ isAnswerSubmitted ? '已提交答案' : '等待作答' }}
            </strong>
          </div>
        </section>

        <section class="assistant-card">
          <div class="assistant-heading">
            <div>
              <span class="section-eyebrow">学习辅助</span>
              <h2>按需获取帮助</h2>
            </div>
            <el-icon class="assistant-heading-icon"><ChatDotRound /></el-icon>
          </div>
          <div class="assistant-tabs" role="tablist" aria-label="学习辅助">
            <button
              type="button"
              class="assistant-tab"
              :class="{ active: activeAssistantTab === 'analysis' }"
              @click="activeAssistantTab = 'analysis'"
            >
              AI 分析
            </button>
            <button
              type="button"
              class="assistant-tab"
              :class="{ active: activeAssistantTab === 'similar' }"
              @click="activeAssistantTab = 'similar'"
            >
              同类练习
            </button>
          </div>

          <div v-if="activeAssistantTab === 'analysis'" class="assistant-tab-content">
          <div class="scroll-area">
            <!-- 加载中 -->
            <div v-if="aiLoading" class="ai-loading">
              <div class="spinner-ring"></div>
              <span>AI 正在深度剖析题目与知识图谱...</span>
            </div>

            <!-- 分析结果 -->
            <div v-else-if="showAiAnalysis && aiAnalysis" class="ai-content">
              <template v-if="aiAnalysis.analysis">
                <!-- 个性化作答剖析（结合学生提交的答案） -->
                <div class="ai-section" v-if="aiAnalysis.analysis.personal">
                  <h4 class="ai-section-title personal-title">个性化作答剖析</h4>
                  <div class="ai-block">
                    <span class="ai-label">你的作答：</span>
                    <span>{{ aiAnalysis.analysis.personal.stu_answer || '（未作答）' }}</span>
                    <span
                      class="verdict-tag"
                      :class="aiAnalysis.analysis.personal.is_correct ? 'correct' : 'wrong'"
                    >
                      {{ aiAnalysis.analysis.personal.is_correct ? '回答正确' : '回答错误' }}
                    </span>
                  </div>
                  <div class="ai-block">
                    <span class="ai-label">判定说明：</span>
                    <span>{{ aiAnalysis.analysis.personal.verdict }}</span>
                  </div>
                  <div class="ai-block" v-if="!aiAnalysis.analysis.personal.is_correct">
                    <span class="ai-label">你的知识误区：</span>
                    <span>{{ aiAnalysis.analysis.personal.personal_misconception }}</span>
                  </div>
                  <div class="ai-block" v-if="!aiAnalysis.analysis.personal.is_correct">
                    <span class="ai-label">针对性纠正：</span>
                    <span>{{ aiAnalysis.analysis.personal.personal_correction }}</span>
                  </div>
                </div>

                <!-- 维度 1：题目与答案深度剖析 -->
                <div class="ai-section">
                  <h4 class="ai-section-title">一、题目与答案深度剖析</h4>
                  <div class="ai-block">
                    <span class="ai-label">核心知识点：</span>
                    <span>{{ aiAnalysis.analysis.aspect1.core_knowledge }}</span>
                  </div>
                  <div class="ai-block">
                    <span class="ai-label">正确选项剖析：</span>
                    <span>{{ aiAnalysis.analysis.aspect1.correct_analysis }}</span>
                  </div>

                  <div class="ai-block" v-if="aiAnalysis.analysis.aspect1.misconceptions && aiAnalysis.analysis.aspect1.misconceptions.length > 0">
                    <span class="ai-label">错误选项误区拆解：</span>
                    <div class="misconception-list">
                      <div
                        v-for="(mis, idx) in aiAnalysis.analysis.aspect1.misconceptions"
                        :key="idx"
                        class="misconception-item"
                      >
                        <div class="mis-option">{{ mis.option }}. {{ mis.content }}</div>
                        <div class="mis-line"><span class="mis-tag wrong">为什么错</span>{{ mis.why_wrong }}</div>
                        <div class="mis-line"><span class="mis-tag trap">知识误区</span>{{ mis.misconception }}</div>
                        <div class="mis-line"><span class="mis-tag fix">如何纠正</span>{{ mis.correction }}</div>
                      </div>
                    </div>
                  </div>

                  <div class="ai-block">
                    <span class="ai-label">总结：</span>
                    <span>{{ aiAnalysis.analysis.aspect1.summary }}</span>
                  </div>
                </div>

                <!-- 维度 2：GraphRAG + 知识图谱局部网络视角 -->
                <div class="ai-section">
                  <h4 class="ai-section-title">二、知识图谱局部网络视角</h4>
                  <div class="ai-block">
                    <span class="ai-label">中心知识点：</span>
                    <span>{{ aiAnalysis.analysis.aspect2.center_node.name }}</span>
                    <span class="ai-type" v-if="aiAnalysis.analysis.aspect2.center_node.type">
                      （{{ aiAnalysis.analysis.aspect2.center_node.type }}）
                    </span>
                  </div>
                  <div class="ai-block" v-if="aiAnalysis.analysis.aspect2.center_node.description">
                    <span class="ai-label">知识点描述：</span>
                    <span>{{ aiAnalysis.analysis.aspect2.center_node.description }}</span>
                  </div>

                  <div class="ai-block" v-if="aiAnalysis.analysis.aspect2.neighbors && aiAnalysis.analysis.aspect2.neighbors.length > 0">
                    <span class="ai-label">1 跳邻居知识点：</span>
                    <div class="neighbor-list">
                      <div
                        v-for="(nb, idx) in aiAnalysis.analysis.aspect2.neighbors"
                        :key="idx"
                        class="neighbor-item"
                      >
                        <span class="neighbor-arrow">{{ nb.direction === 'out' ? '→' : '←' }}</span>
                        <span class="neighbor-name">{{ nb.node_name }}</span>
                        <span class="neighbor-rel">「{{ nb.relationship_name }}」</span>
                      </div>
                    </div>
                  </div>

                  <div class="ai-block">
                    <span class="ai-label">知识网络关联分析：</span>
                    <span>{{ aiAnalysis.analysis.aspect2.knowledge_network_analysis }}</span>
                  </div>
                  <div class="ai-block">
                    <span class="ai-label">学习建议：</span>
                    <span>{{ aiAnalysis.analysis.aspect2.learning_suggestion }}</span>
                  </div>
                </div>
              </template>

              <!-- 分析失败提示 -->
              <div v-else class="ai-error">
                <el-icon class="mr-2"><Warning /></el-icon>
                <span>{{ aiAnalysis.error_message || 'AI 分析暂不可用' }}</span>
              </div>
            </div>

            <!-- 未触发分析 -->
            <div class="flex items-center justify-center h-full" v-else>
              <el-button type="primary" plain @click="triggerAiAnalysis" :disabled="!isAnswerSubmitted || aiLoading">
                {{ isAnswerSubmitted ? '获取 AI 分析' : '请先提交答案' }}
              </el-button>
            </div>
            <div class="spacer"></div>
          </div>
          </div>

          <div v-else class="assistant-tab-content">
          <div class="scroll-area">
            <div v-if="showSimilarQuestions">
              <div v-if="similarLoading" class="similar-state">
                <div class="spinner-ring small"></div>
                <span>正在根据本题推荐练习...</span>
              </div>
              <ul class="similar-list" v-else-if="similarQuestions.length > 0">
                <li
                  v-for="sim in similarQuestions"
                  :key="sim.question_id"
                  class="similar-item"
                  tabindex="0"
                  @click="openSimilarQuestion(sim)"
                  @keydown.enter="openSimilarQuestion(sim)"
                >
                  <span class="dot"></span>
                  <div class="similar-body">
                    <span class="text">{{ sim.question_description }}</span>
                    <span class="similar-meta">
                      <span v-if="sim.kg_node_name">{{ sim.kg_node_name }}</span>
                      <span>{{ questionTypeLabel(sim.question_type) }}</span>
                      <span>难度 {{ sim.question_difficulty }}</span>
                    </span>
                  </div>
                  <el-button size="small" type="success" plain class="go-btn" @click.stop="openSimilarQuestion(sim)">去练习</el-button>
                </li>
              </ul>
              <div v-else class="similar-state">
                <span>暂无匹配的同类题，请先完成更多练习。</span>
              </div>
            </div>
            <div class="flex items-center justify-center h-full" v-else>
              <el-button type="success" plain @click="triggerSimilarQuestions" :disabled="!isAnswerSubmitted || similarLoading">
                {{ isAnswerSubmitted ? '举一反三' : '请先提交答案' }}
              </el-button>
            </div>
            <div class="spacer"></div>
          </div>
          </div>
        </section>
      </aside>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Warning } from '@element-plus/icons-vue'
import BorderGlow from '@/components/BorderGlow.vue'
import {
  fetchQuestions,
  fetchQuestionById,
  fetchSimilarQuestions,
  submitExerciseRecord,
  fetchSocraticHint,
  type Question,
  type SocraticHintResponse,
} from '@/api/practice'
import { fetchQuestionAnalysis, type QuestionAnalysisResult } from '@/api/questionAnalysis'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const questions = ref<Question[]>([])
const currentIndex = ref(0)
const loading = ref(true)
const isAnswerSubmitted = ref(false)
const showAiAnalysis = ref(false)
const showSimilarQuestions = ref(false)
const activeAssistantTab = ref<'analysis' | 'similar'>('analysis')

// 学生已提交的答案字符串（用于 AI 个性化作答剖析）
const submittedAnswer = ref('')

// 全量 ID 数组缓存（用于仪表盘跳转后的前后切换）
const cachedIdList = ref<number[]>([])
const cachedIndex = ref(0)

const currentQuestion = computed(() => {
  return questions.value[currentIndex.value] || null
})
const totalQuestions = computed(() => cachedIdList.value.length || questions.value.length)
const currentQuestionNumber = computed(() => (
  cachedIdList.value.length > 0 ? cachedIndex.value + 1 : currentIndex.value + 1
))
const questionProgress = computed(() => (
  totalQuestions.value > 0 ? (currentQuestionNumber.value / totalQuestions.value) * 100 : 0
))
const practiceNodeName = computed(() => {
  const value = route.query.kgNodeName
  return typeof value === 'string' ? value.trim() : ''
})
const emptyQuestionMessage = computed(() => (
  practiceNodeName.value ? `暂无“${practiceNodeName.value}”对应的题目` : '暂无题目'
))

// AI 分析与解惑（双维度：题目答案深度剖析 + 知识图谱局部网络视角）
const aiAnalysis = ref<QuestionAnalysisResult | null>(null)
const aiLoading = ref(false)
const similarQuestions = ref<Question[]>([])
const similarLoading = ref(false)

const elapsedSeconds = ref(0)
const hintLevel = ref(1)
const hintLoading = ref(false)
const hintHistory = ref<SocraticHintResponse[]>([])
let questionStartedAt: number | null = null
let questionTimer: ReturnType<typeof setInterval> | null = null

const userAnswer = ref('')
const userAnswerArray = ref<string[]>([])

const remainingHintSeconds = computed(() => Math.max(0, 60 - elapsedSeconds.value))
const hintUnlocked = computed(() => elapsedSeconds.value >= 60)
const canRequestHint = computed(() => (
  Boolean(currentQuestion.value)
  && !isAnswerSubmitted.value
  && hintUnlocked.value
  && !hintLoading.value
  && hintLevel.value <= 3
))
const hintStatusText = computed(() => {
  if (isAnswerSubmitted.value) return '本题已提交，不能继续请求提示'
  if (!hintUnlocked.value) return `请先独立思考，还需 ${remainingHintSeconds.value} 秒`
  if (hintLevel.value > 3) return '本题的分级提示已全部使用'
  return '可以请求下一层思路引导'
})
const hintButtonText = computed(() => {
  if (hintLevel.value > 3) return '提示已用完'
  return `获取第 ${hintLevel.value} 级提示`
})

const stopQuestionTimer = () => {
  if (questionTimer !== null) {
    clearInterval(questionTimer)
    questionTimer = null
  }
  questionStartedAt = null
}

const startQuestionTimer = () => {
  stopQuestionTimer()
  questionStartedAt = Date.now()
  elapsedSeconds.value = 0
  questionTimer = setInterval(() => {
    if (questionStartedAt !== null) {
      elapsedSeconds.value = Math.floor((Date.now() - questionStartedAt) / 1000)
    }
  }, 1000)
}

onMounted(async () => {
  const courseIdStr = route.query.module as string
  const questionIdStr = route.query.questionId as string
  const idListStr = route.query.idList as string
  const randomIndexStr = route.query.randomIndex as string
  const courseId = courseIdStr ? parseInt(courseIdStr, 10) : undefined
  const kgNodeName = practiceNodeName.value || undefined
  const questionId = questionIdStr ? parseInt(questionIdStr, 10) : undefined

  if (!courseId && !questionId && !kgNodeName) {
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
    } else if (courseId || kgNodeName) {
      // 按学科或知识点加载题目；仅传知识点时从全部题目中筛选
      const data = await fetchQuestions(courseId, kgNodeName)
      questions.value = data || []
    }
  } catch (error) {
    console.error('Failed to fetch questions:', error)
    ElMessage.error('获取题目失败')
  } finally {
    loading.value = false
    if (currentQuestion.value) {
      startQuestionTimer()
    }
  }
})

onUnmounted(() => {
  stopQuestionTimer()
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
  const answerStr = getCurrentAnswer()

  // 保存学生答案，供 AI 个性化作答剖析使用
  submittedAnswer.value = answerStr

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
    stopQuestionTimer()
    ElMessage.success('答案已提交')
  } catch (error) {
    console.error('提交答案失败:', error)
    ElMessage.error('提交答案失败，请重试')
  }
}

const getCurrentAnswer = () => (
  userAnswerArray.value.length > 0
    ? [...userAnswerArray.value].sort().join(',')
    : userAnswer.value.trim()
)

const requestSocraticHint = async () => {
  if (!currentQuestion.value || !canRequestHint.value) return

  hintLoading.value = true
  try {
    const result = await fetchSocraticHint({
      question_id: currentQuestion.value.question_id,
      student_attempt: getCurrentAnswer(),
      elapsed_seconds: elapsedSeconds.value,
      hint_level: hintLevel.value,
    })
    hintHistory.value.push(result)
    hintLevel.value = Math.min(4, result.hint_level + 1)
    ElMessage.success(`已生成第 ${result.hint_level} 级提示`)
  } catch (error: any) {
    console.error('获取苏格拉底式提示失败:', error)
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || 'AI 提示暂时不可用，请稍后重试')
  } finally {
    hintLoading.value = false
  }
}

const triggerAiAnalysis = async () => {
  if (!currentQuestion.value) return
  if (aiLoading.value) return

  activeAssistantTab.value = 'analysis'
  aiLoading.value = true
  showAiAnalysis.value = true
  aiAnalysis.value = null
  try {
    const stuId = authStore.user?.id
    const result = await fetchQuestionAnalysis(
      currentQuestion.value.question_id,
      submittedAnswer.value || undefined,
      stuId,
    )
    aiAnalysis.value = result
    if (result.status === 'db_error') {
      ElMessage.error(result.error_message || 'AI 分析服务异常，请稍后重试')
    } else if (result.status === 'no_data') {
      ElMessage.warning(result.error_message || '题目数据不存在，无法分析')
    }
  } catch (error) {
    console.error('获取 AI 分析失败:', error)
    aiAnalysis.value = null
    ElMessage.error('获取 AI 分析失败，请稍后重试')
  } finally {
    aiLoading.value = false
  }
}

const questionTypeLabel = (questionType: string) => {
  const labels: Record<string, string> = {
    single_choice: '单选题',
    choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    T_or_F: '判断题',
    fill_blanks: '填空题',
    Fill_blanks: '填空题',
    fill_Blanks: '填空题',
    Q_A: '简答题',
    q_a: '简答题',
  }
  return labels[questionType] || questionType
}

const triggerSimilarQuestions = async () => {
  if (!currentQuestion.value || !isAnswerSubmitted.value || similarLoading.value) return

  activeAssistantTab.value = 'similar'
  showSimilarQuestions.value = true
  similarQuestions.value = []
  similarLoading.value = true
  try {
    similarQuestions.value = await fetchSimilarQuestions(currentQuestion.value.question_id)
  } catch (error) {
    console.error('获取同类题推荐失败:', error)
    ElMessage.error('同类题推荐暂时不可用，请稍后重试')
  } finally {
    similarLoading.value = false
  }
}

const openSimilarQuestion = (question: Question) => {
  questions.value = [question]
  currentIndex.value = 0
  cachedIdList.value = []
  cachedIndex.value = 0
  resetAnswer()
  activeAssistantTab.value = 'analysis'
  ElMessage.success('已切换至推荐题目')
}

const resetAnswer = () => {
  stopQuestionTimer()
  userAnswer.value = ''
  userAnswerArray.value = []
  isAnswerSubmitted.value = false
  showAiAnalysis.value = false
  showSimilarQuestions.value = false
  similarQuestions.value = []
  similarLoading.value = false
  activeAssistantTab.value = 'analysis'
  aiAnalysis.value = null
  aiLoading.value = false
  submittedAnswer.value = ''
  hintLevel.value = 1
  hintHistory.value = []
  if (currentQuestion.value) {
    startQuestionTimer()
  }
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

.socratic-help-panel {
  margin-top: 18px;
  padding: 14px 16px;
  border: 1px solid rgba(64, 158, 255, 0.28);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.08), rgba(255, 255, 255, 0.45));
}

.socratic-help-header,
.socratic-help-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.socratic-help-title {
  color: #2563a8;
  font-size: 0.95rem;
  font-weight: 600;
}

.socratic-help-status,
.socratic-help-description,
.socratic-help-limit {
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.5;
}

.socratic-help-status {
  margin-top: 3px;
}

.socratic-help-description {
  margin: 10px 0;
}

.socratic-hint-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.socratic-hint-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.55;
}

.socratic-hint-item span:last-child {
  white-space: pre-wrap;
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
  cursor: pointer;
  transition: background-color 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.similar-item:hover,
.similar-item:focus-visible {
  background: rgba(255, 255, 255, 0.78);
  outline: none;
  box-shadow: 0 0 0 2px rgba(39, 174, 96, 0.18);
}

.similar-body {
  flex: 1;
  min-width: 0;
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
  display: block;
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.similar-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  color: #6b7280;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.similar-state {
  display: flex;
  min-height: 180px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #6b7280;
  font-size: 0.9rem;
  text-align: center;
}

.spinner-ring.spinner-ring.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

.go-btn {
  margin-left: 12px;
}

.mock-item {
  opacity: 0.5;
}

/* --- AI 分析与解惑样式 --- */
.ai-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 0;
  color: #2980b9;
  font-size: 0.95rem;
}

.spinner-ring {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(41, 128, 185, 0.2);
  border-top-color: #2980b9;
  border-radius: 50%;
  animation: ai-spin 0.8s linear infinite;
}

@keyframes ai-spin {
  to { transform: rotate(360deg); }
}

.ai-section {
  margin-bottom: 20px;
}

.ai-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #2980b9;
  margin: 0 0 12px 0;
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(41, 128, 185, 0.3);
}

.personal-title {
  color: #8e44ad;
  border-bottom-color: rgba(142, 68, 173, 0.3);
}

.verdict-tag {
  display: inline-block;
  margin-left: 8px;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  vertical-align: middle;
}

.verdict-tag.correct { background: #27ae60; }
.verdict-tag.wrong { background: #e74c3c; }

.ai-block {
  margin-bottom: 12px;
  line-height: 1.7;
  font-size: 0.92rem;
  color: #333;
}

.ai-label {
  font-weight: 600;
  color: #2c3e50;
}

.ai-type {
  color: #7f8c8d;
  font-size: 0.85rem;
}

.misconception-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.misconception-item {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 10px 12px;
}

.mis-option {
  font-weight: 600;
  color: #c0392b;
  margin-bottom: 6px;
}

.mis-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 0.88rem;
  line-height: 1.6;
}

.mis-tag {
  flex-shrink: 0;
  font-size: 0.75rem;
  padding: 1px 6px;
  border-radius: 4px;
  color: #fff;
  margin-top: 2px;
}

.mis-tag.wrong { background: #e74c3c; }
.mis-tag.trap { background: #f39c12; }
.mis-tag.fix { background: #27ae60; }

.neighbor-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.neighbor-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.4);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 0.88rem;
}

.neighbor-arrow {
  color: #27ae60;
  font-weight: 600;
}

.neighbor-name {
  font-weight: 600;
  color: #2c3e50;
}

.neighbor-rel {
  color: #7f8c8d;
  font-size: 0.82rem;
}

.ai-error {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(231, 76, 60, 0.08);
  color: #c0392b;
  border-radius: 8px;
  font-size: 0.92rem;
}
/* --- 学习工作台重排：单主任务流 + 辅助栏 --- */
.practice-page {
  min-height: calc(100vh - 164px);
  height: auto;
  margin: 0;
  color: var(--workspace-text);
}

.practice-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: calc(100vh - 164px);
  height: auto;
  padding: 0;
}

.practice-toolbar {
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 62px;
  padding: 12px 16px;
  border: 1px solid var(--workspace-border);
  border-radius: var(--workspace-radius);
  background: var(--workspace-surface);
  box-shadow: var(--workspace-shadow-card);
}

.practice-toolbar-context {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
  min-width: 190px;
}

.practice-toolbar-context strong {
  color: var(--workspace-heading);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.section-eyebrow {
  display: block;
  color: var(--workspace-subtle-text);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .08em;
  line-height: 1.4;
  text-transform: uppercase;
}

.practice-progress {
  position: relative;
  flex: 1;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--workspace-surface-muted);
}

.practice-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--workspace-primary), var(--workspace-accent));
  transition: width .25s ease;
}

.question-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.question-actions :deep(.el-button) {
  margin: 0;
}

.practice-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(290px, 330px);
  align-items: start;
  gap: 16px;
  min-width: 0;
}

.question-panel,
.session-card,
.assistant-card {
  border: 1px solid var(--workspace-border);
  border-radius: 14px;
  background: var(--workspace-surface);
  box-shadow: var(--workspace-shadow-card);
}

.question-panel {
  min-width: 0;
  min-height: 650px;
  overflow: visible;
}

.question-panel .section-container {
  display: block;
  flex: none;
  overflow: visible;
  padding: 28px 30px 22px;
}

.question-intro {
  margin-bottom: 22px;
}

.question-title {
  margin: 5px 0 0;
  color: var(--workspace-heading);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -.02em;
}

.question-panel .relative-area,
.question-panel .scroll-area {
  max-height: none;
  overflow: visible;
  padding-right: 0;
}

.question-panel .spacer,
.review-section .spacer,
.assistant-tab-content .spacer {
  display: none;
}

.stem-content {
  padding: 20px 22px;
  border: 1px solid var(--workspace-border);
  border-radius: 12px;
  background: var(--workspace-surface-muted);
  color: var(--workspace-heading);
  font-size: 17px;
  line-height: 1.8;
}

.answer-area {
  margin-top: 26px;
  padding-top: 24px;
  border-top: 1px solid var(--workspace-border);
}

.answer-title {
  margin: 0 0 12px;
  color: var(--workspace-heading);
  font-size: 15px;
  font-weight: 700;
}

.custom-radio-group,
.custom-checkbox-group {
  width: 100%;
  align-items: stretch;
  gap: 10px;
}

.custom-radio-group :deep(.el-radio),
.custom-checkbox-group :deep(.el-checkbox) {
  width: 100%;
  min-height: 48px;
  box-sizing: border-box;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--workspace-border);
  border-radius: 10px;
  background: #fff;
  color: var(--workspace-text);
  transition: border-color .18s ease, background-color .18s ease, box-shadow .18s ease;
}

.custom-radio-group :deep(.el-radio:hover),
.custom-checkbox-group :deep(.el-checkbox:hover) {
  border-color: var(--workspace-primary-border);
  background: var(--workspace-primary-soft);
}

.custom-radio-group :deep(.el-radio.is-checked),
.custom-checkbox-group :deep(.el-checkbox.is-checked) {
  border-color: var(--workspace-primary);
  background: var(--workspace-primary-soft);
  box-shadow: 0 0 0 2px rgba(33, 70, 155, .08);
}

.custom-radio-group :deep(.el-radio__label),
.custom-checkbox-group :deep(.el-checkbox__label) {
  flex: 1;
  color: inherit;
  font-size: 15px;
  line-height: 1.5;
  white-space: normal;
}

.question-panel :deep(.el-textarea__inner) {
  border-color: var(--workspace-border);
  background: var(--workspace-surface-muted);
  box-shadow: none;
}

.socratic-help-panel {
  margin-top: 24px;
  padding: 16px 18px;
  border: 1px solid var(--workspace-primary-border);
  border-radius: 12px;
  background: var(--workspace-primary-soft);
}

.socratic-help-title { color: var(--workspace-primary); }

.socratic-hint-item {
  border: 1px solid rgba(33, 70, 155, .1);
  background: rgba(255, 255, 255, .72);
}

.review-section {
  margin: 0 30px 30px;
  padding-top: 24px;
  border-top: 1px solid var(--workspace-border);
}

.review-heading,
.session-card-heading,
.assistant-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.review-title,
.session-card-heading h2,
.assistant-heading h2 {
  margin: 4px 0 0;
  color: var(--workspace-heading);
  font-size: 16px;
  font-weight: 700;
}

.explanation-content {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid var(--workspace-accent-soft);
  border-radius: 10px;
  background: #f4fbf9;
  color: var(--workspace-text);
  line-height: 1.75;
}

.unsubmitted-notice {
  justify-content: flex-start;
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #f1dfbd;
  border-radius: 10px;
  background: #fff9ed;
  color: #8a5a13;
  font-size: 13px;
}

.practice-sidebar {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 16px;
}

.session-card { padding: 18px 20px; }

.session-count {
  color: var(--workspace-primary);
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  margin-top: 14px;
  border-top: 1px solid var(--workspace-border);
  color: var(--workspace-muted);
  font-size: 13px;
}

.session-row strong {
  max-width: 170px;
  overflow: hidden;
  color: var(--workspace-heading);
  font-size: 13px;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-row strong.is-success { color: var(--workspace-accent); }
.session-row strong.is-pending { color: var(--workspace-warning); }

.assistant-card {
  display: flex;
  min-height: 420px;
  flex-direction: column;
  overflow: hidden;
}

.assistant-heading { padding: 18px 20px 14px; }

.assistant-heading-icon {
  color: var(--workspace-primary);
  font-size: 18px;
}

.assistant-tabs {
  display: flex;
  gap: 4px;
  padding: 0 20px;
  border-bottom: 1px solid var(--workspace-border);
}

.assistant-tab {
  position: relative;
  min-height: 40px;
  padding: 0 6px;
  border: 0;
  color: var(--workspace-muted);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  transition: color .18s ease;
}

.assistant-tab::after {
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: transparent;
  content: '';
}

.assistant-tab:hover,
.assistant-tab.active { color: var(--workspace-primary); }
.assistant-tab.active { font-weight: 600; }
.assistant-tab.active::after { background: var(--workspace-primary); }

.assistant-tab-content {
  min-height: 0;
  flex: 1;
}

.assistant-tab-content > .scroll-area {
  min-height: 180px;
  max-height: calc(100vh - 360px);
  overflow-y: auto;
  padding: 18px 20px 20px;
}

.assistant-tab-content > .scroll-area > .flex { min-height: 180px; }

.assistant-card .title-blue,
.assistant-card .title-green { color: var(--workspace-heading); }

.assistant-card .ai-section-title {
  margin-top: 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--workspace-border);
  color: var(--workspace-primary);
  font-size: 14px;
}

.assistant-card .personal-title {
  color: var(--workspace-accent);
  border-bottom-color: var(--workspace-accent-soft);
}

.assistant-card .ai-block {
  font-size: 13px;
  line-height: 1.7;
}

.assistant-card .similar-list { gap: 8px; }

.assistant-card .similar-item {
  padding: 10px 12px;
  border: 1px solid var(--workspace-border);
  background: #fff;
}

.assistant-card .similar-item .dot { background: var(--workspace-primary); }

.assistant-card .go-btn {
  color: var(--workspace-primary);
  border-color: var(--workspace-primary-border);
}

@media (max-width: 1040px) {
  .practice-workspace { grid-template-columns: minmax(0, 1fr) 280px; }
  .practice-toolbar-context { min-width: 160px; }
  .question-actions :deep(.el-button) { padding-inline: 9px; }
}

@media (max-width: 820px) {
  .practice-workspace { grid-template-columns: 1fr; }
  .practice-sidebar {
    display: grid;
    grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr);
  }
  .assistant-card { min-height: 360px; }
  .assistant-tab-content > .scroll-area { max-height: 420px; }
}

@media (max-width: 620px) {
  .practice-toolbar { flex-wrap: wrap; gap: 10px 14px; }
  .practice-toolbar-context { min-width: 0; flex: 1 1 auto; }
  .practice-progress { order: 3; flex-basis: 100%; }
  .question-actions { margin-left: auto; }
  .question-panel .section-container { padding: 22px 18px 18px; }
  .review-section { margin-inline: 18px; }
  .practice-sidebar { display: flex; }
  .stem-content { padding: 16px; font-size: 16px; }
}

@media (prefers-reduced-motion: reduce) {
  .practice-progress span,
  .custom-radio-group :deep(.el-radio),
  .custom-checkbox-group :deep(.el-checkbox),
  .assistant-tab { transition: none; }
}
</style>
