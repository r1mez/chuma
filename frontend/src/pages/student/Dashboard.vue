<template>
  <BorderGlow class="dashboard-page" background-color="transparent">
    <div class="dashboard-layout">
      <!-- 左侧面板：个人信息与建议 -->
      <div class="left-panel">
        <!-- 个人信息 -->
        <div class="glass-card personal-info">
          <div class="card-header-row">
            <h3 class="card-title">个人信息</h3>
            <el-button type="primary" size="small" :icon="Edit" @click="openEditDialog">编辑个人信息</el-button>
          </div>
          <div class="info-content">
            <div class="avatar-placeholder">{{ genderAvatar }}</div>
            <div class="info-text">
              <p><strong>姓名：</strong>{{ userName }}</p>
              <p><strong>Email：</strong>{{ userEmail }}</p>
              <p><strong>座右铭：</strong>{{ motto || '还没有设置座右铭' }}</p>
              <p v-if="userClass"><strong>班级：</strong>{{ userClass }}</p>
              <p v-if="stuLevel" class="rating-row">
                <strong>评级：</strong>
                <span class="rating-badge" :style="{ color: ratingColor }">{{ stuLevel }}</span>
              </p>
            </div>
          </div>
        </div>

        <!-- AI 助学建议面板 -->
        <div class="glass-card ai-analysis-panel">
          <div class="card-header-row">
            <h3 class="card-title ai-suggest-title">AI 助学建议</h3>
          </div>

          <div class="analysis-scroll-area">
            <!-- 未分析状态：显示按钮 -->
            <div v-if="!analysisResult && !analysisLoading" class="analysis-idle">
              <p class="analysis-desc">基于你的知识图谱掌握度、错题记录和个人评级，AI 将生成个性化的学习分析报告。</p>
              <el-button
                type="primary"
                size="large"
                class="analysis-trigger-btn"
                :icon="Aim"
                @click="triggerAnalysis"
              >
                开始 AI 分析
              </el-button>
            </div>

            <!-- 加载状态：旋转加载特效 -->
            <div v-if="analysisLoading" class="analysis-loading">
              <div class="spinner-container">
                <div class="analysis-spinner"></div>
                <div class="spinner-ring spinner-ring-1"></div>
                <div class="spinner-ring spinner-ring-2"></div>
              </div>
              <p class="loading-text">AI 正在分析你的学习数据...</p>
              <p class="loading-subtext">正在综合评估知识图谱、错题记录与个人评级</p>
            </div>

            <!-- 分析完成状态：展示结果 -->
            <div v-if="analysisResult && !analysisLoading" class="analysis-result">
              <!-- 综合评级 -->
              <div class="result-rating-row">
                <span class="result-label">综合评级</span>
                <span
                  class="result-rating-badge"
                  :style="{ color: getRatingColor(analysisResult.analysis?.comprehensive_rating || '') }"
                >
                  {{ analysisResult.analysis?.comprehensive_rating || 'N/A' }}
                </span>
              </div>

              <!-- 维度可用性指示 -->
              <div class="dimension-indicators">
                <span
                  v-for="dim in dimensionLabels"
                  :key="dim.key"
                  class="dimension-tag"
                  :class="dim.available ? 'dim-available' : 'dim-missing'"
                >
                  {{ dim.label }}
                </span>
              </div>

              <!-- 分析内容 -->
              <div class="analysis-content" v-if="analysisResult.analysis">
                <div class="analysis-section">
                  <h4 class="section-title">总体概述</h4>
                  <p class="section-text">{{ analysisResult.analysis.summary }}</p>
                </div>
                <div class="analysis-section">
                  <h4 class="section-title">薄弱环节</h4>
                  <p class="section-text">{{ analysisResult.analysis.weakness_analysis }}</p>
                </div>
                <div class="analysis-section">
                  <h4 class="section-title">改进建议</h4>
                  <p class="section-text">{{ analysisResult.analysis.improvement_suggestions }}</p>
                </div>
                <div class="analysis-section" v-if="analysisResult.analysis.priority_focus?.length">
                  <h4 class="section-title">优先攻克知识点</h4>
                  <div class="priority-list">
                    <span
                      v-for="(item, idx) in analysisResult.analysis.priority_focus"
                      :key="idx"
                      class="priority-chip"
                    >
                      {{ idx + 1 }}. {{ item }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- 重新分析按钮 -->
              <el-button
                type="primary"
                size="small"
                plain
                class="reanalyze-btn"
                :icon="Refresh"
                @click="triggerAnalysis"
              >
                重新分析
              </el-button>
            </div>

            <!-- 分析出错状态 -->
            <div v-if="analysisError && !analysisLoading" class="analysis-error">
              <p class="error-text">{{ analysisError }}</p>
              <el-button type="primary" size="small" @click="triggerAnalysis">重试</el-button>
            </div>

            <!-- 老师建议与评估（功能开发中） -->
            <div class="teacher-section">
              <div class="section-divider"></div>
              <h4 class="teacher-title">老师建议与评估</h4>
              <p class="teacher-placeholder">功能开发中，敬请期待...</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧面板：408 考研四宫格学科 -->
      <div class="right-panel">
        <div class="glass-card daily-question-card">
          <div class="card-header-row">
            <h3 class="card-title">今日一题</h3>
            <span v-if="dailyQuestions.length" class="daily-question-date">{{ dailyQuestions[0].target_date }}</span>
          </div>
          <template v-if="dailyQuestions.length">
            <div class="daily-question-list">
              <div v-for="question in dailyQuestions" :key="question.daily_question_id" class="daily-question-item">
                <div class="daily-question-item-header">
                  <p class="daily-question-meta">
                    {{ question.course_name }}<span v-if="question.kg_node_name"> · {{ question.kg_node_name }}</span>
                  </p>
                  <el-tag v-if="question.completed" size="small" type="success">已完成</el-tag>
                </div>
                <p class="daily-question-text">{{ question.question_description }}</p>
                <p v-if="question.recommendation_reason" class="daily-question-reason">
                  推荐理由：{{ question.recommendation_reason }}
                </p>
                <el-button type="primary" size="small" plain @click="navigateToDailyQuestion(question)">
                  {{ question.completed ? '再次练习' : '开始今日一题' }}
                </el-button>
              </div>
            </div>
          </template>
          <p v-else class="daily-question-empty">四个学科的每日一题将在 4:30 后自动生成；若定时任务未完成，打开页面时会自动补生成。</p>
        </div>

        <div v-for="subject in subjects" :key="subject.id" class="glass-card subject-card">
          <h3 class="subject-title">{{ subject.name }}</h3>

          <!-- 核心需求：跑道进度条设计 -->
          <div class="runway-container" :title="`掌握度: ${subject.progress}%`">
            <!-- 横线跑道 -->
            <div class="runway-line"></div>
            <!-- 终点红旗 (竖线与旗帜) -->
            <div class="finish-line">
              <div class="flag-pole"></div>
              <div class="flag-cloth"></div>
            </div>
            <!-- 进度条 (基于进度动态定位) -->
            <div class="progress-bar" :style="{ left: `calc(${subject.progress}% - 12px)` }">
              🚀
            </div>
          </div>

          <!-- 最新与做题记录跳转列表 -->
          <div class="action-list">
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.latestMsg }}</span>
              <!-- 跳转到 题目练习面板（携带随机题目 ID 和题目列表） -->
              <el-button size="small" type="primary" plain @click="navigateToPractice(subject, 'new')" :disabled="!subject.newQuestionId">跳转练习</el-button>
            </div>
            <div class="action-item">
              <span class="action-desc text-truncate">{{ subject.recordMsg }}</span>
              <!-- 跳转到 题目练习面板（携带做题记录中的随机题目 ID 和题目列表） -->
              <el-button size="small" type="warning" plain @click="navigateToPractice(subject, 'record')" :disabled="!subject.recordQuestionId">做题记录</el-button>
            </div>
          </div>

          <div class="next-step-row">
            <div class="next-step-copy">
              <span class="next-step-label">下一知识点</span>
              <strong>{{ subject.nextKnowledgePoint || '暂无可用推荐' }}</strong>
            </div>
            <el-button
              size="small"
              type="success"
              plain
              :disabled="!subject.nextQuestionId"
              @click="navigateToRecommendedPractice(subject)"
            >
              去学习
            </el-button>
          </div>

          <!-- 知识图谱全宽按钮 -->
          <el-button class="full-width-btn" type="success" plain @click="navigateTo('/student/knowledge', subject.id)">
            {{ subject.name }} 知识图谱
          </el-button>
        </div>
      </div>
    </div>

    <!-- 编辑个人信息弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑个人信息"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="80px" class="edit-form">
        <el-form-item label="姓名">
          <el-input v-model="editForm.stu_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.stu_email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="editForm.stu_gender" placeholder="请选择性别" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
            <el-option label="保密" value="保密" />
          </el-select>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="editForm.stu_pwd" type="password" placeholder="留空则不修改密码" show-password />
        </el-form-item>
        <el-form-item label="座右铭">
          <el-input
            v-model="editForm.motto"
            type="textarea"
            :rows="2"
            placeholder="请输入您的座右铭"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSaveProfile">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Aim, Refresh } from '@element-plus/icons-vue'
import BorderGlow from '@/components/BorderGlow.vue'
import { fetchCourses, fetchDashboardNewQuestion, fetchDashboardRecordQuestion, type Course } from '@/api/practice'
import { fetchCurrentUser, updateProfile } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { fetchStuAnalysis, type StuAnalysisResult } from '@/api/analysis'
import { fetchDashboardProgress, fetchDailyQuestion, type DailyQuestion } from '@/api/learning'
import { fetchNextKnowledgePoints } from '@/api/learningPlan'

const router = useRouter()
const authStore = useAuthStore()

// ========== 个人信息（从数据库/Store 获取） ==========
const userName = ref('加载中...')
const userEmail = ref('')
const userGender = ref<string | null>(null)
const stuLevel = ref<string | null>(null)
const userClass = ref<string | null>(null)

// 座右铭仅存前端 localStorage，不从数据库获取
const MOTTO_KEY = 'chuma_user_motto'
const motto = ref(localStorage.getItem(MOTTO_KEY) || '')

// 头像根据性别显示
const genderAvatar = computed(() => {
  if (userGender.value === '女') return '👩‍🎓'
  if (userGender.value === '男') return '👨‍🎓'
  return '🧑'
})

// 评级颜色映射：A-绿色、B-蓝色、C-黄色、D-红色、E-黑色
const ratingColorMap: Record<string, string> = {
  A: '#67c23a',
  B: '#409eff',
  C: '#e6a23c',
  D: '#f56c6c',
  E: '#303133',
}
const ratingColor = computed(() => {
  if (!stuLevel.value) return '#303133'
  const key = stuLevel.value.toUpperCase()
  return ratingColorMap[key] || '#303133'
})

// ========== AI 学习分析 ==========
const analysisLoading = ref(false)
const analysisResult = ref<StuAnalysisResult | null>(null)
const analysisError = ref('')

/** 评级颜色映射（复用） */
const getRatingColor = (rating: string): string => {
  const key = rating.toUpperCase()
  return ratingColorMap[key] || '#303133'
}

/** 维度标签与可用性 */
const dimensionLabels = computed(() => {
  const detail = analysisResult.value?.dimensions_detail
  return [
    { key: 'level', label: '个人评级', available: !!detail?.level?.available },
    { key: 'mastery', label: '知识图谱', available: !!detail?.mastery?.available },
    { key: 'wrong', label: '错题记录', available: !!detail?.wrong_exercises?.available },
  ]
})

/** 触发 AI 分析 */
const triggerAnalysis = async () => {
  const userId = authStore.user?.id
  if (!userId) {
    ElMessage.warning('无法获取用户信息，请重新登录')
    return
  }

  analysisLoading.value = true
  analysisResult.value = null
  analysisError.value = ''

  try {
    const result = await fetchStuAnalysis(userId)
    if (result.error) {
      analysisError.value = result.error
    } else {
      analysisResult.value = result
      // 分析完成后刷新个人信息，同步展示最新评级（stu_level 已写回数据库）
      await loadUserInfo()
    }
  } catch (err: any) {
    console.error('AI 分析失败:', err)
    let msg = 'AI 分析请求失败，请稍后重试'
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') {
      msg = detail
    } else if (err?.message) {
      msg = err.message
    }
    analysisError.value = msg
  } finally {
    analysisLoading.value = false
  }
}

/** 加载当前用户信息 */
const loadUserInfo = async () => {
  try {
    const me = await fetchCurrentUser()
    userName.value = me.name || '未知用户'
    userEmail.value = me.email || ''
    userGender.value = me.gender || null
    stuLevel.value = me.stu_level || null
    userClass.value = me.class_name || null
    // 同步到 Store
    authStore.setUser({
      id: me.id,
      name: me.name,
      email: me.email,
      gender: me.gender,
      stu_level: me.stu_level,
      class_id: me.class_id,
      class_name: me.class_name,
      role: me.user_type as 'student' | 'teacher',
    })
  } catch {
    // 接口失败时降级使用 Store 中的已有信息
    if (authStore.user) {
      userName.value = authStore.user.name
      userEmail.value = authStore.user.email || ''
      userGender.value = authStore.user.gender
      stuLevel.value = authStore.user.stu_level || null
      userClass.value = authStore.user.class_name || null
    }
  }
}

// ========== 编辑弹窗 ==========
const editDialogVisible = ref(false)
const saving = ref(false)

const editForm = ref({
  stu_name: '',
  stu_email: '',
  stu_gender: '',
  stu_pwd: '',
  motto: '',
})

const openEditDialog = () => {
  editForm.value = {
    stu_name: userName.value === '加载中...' ? '' : userName.value,
    stu_email: userEmail.value,
    stu_gender: userGender.value || '',
    stu_pwd: '',
    motto: motto.value,
  }
  editDialogVisible.value = true
}

const handleSaveProfile = async () => {
  saving.value = true
  try {
    // 1. 保存数据库字段（姓名、邮箱、性别、密码）到后端
    const updateData: Record<string, string> = {}
    if (editForm.value.stu_name) updateData.stu_name = editForm.value.stu_name
    if (editForm.value.stu_email) updateData.stu_email = editForm.value.stu_email
    if (editForm.value.stu_gender) updateData.stu_gender = editForm.value.stu_gender
    if (editForm.value.stu_pwd) updateData.stu_pwd = editForm.value.stu_pwd

    if (Object.keys(updateData).length > 0) {
      await updateProfile(updateData)
    }

    // 2. 保存座右铭到 localStorage（仅前端）
    localStorage.setItem(MOTTO_KEY, editForm.value.motto)
    motto.value = editForm.value.motto

    // 3. 更新页面显示和 Store
    userName.value = editForm.value.stu_name || userName.value
    userEmail.value = editForm.value.stu_email || userEmail.value
    userGender.value = editForm.value.stu_gender || userGender.value

    if (authStore.user) {
      authStore.setUser({
        ...authStore.user,
        name: userName.value,
        email: userEmail.value,
        gender: userGender.value,
      })
    }

    editDialogVisible.value = false
    ElMessage.success('个人信息已保存')
  } catch (err: any) {
    console.error('保存个人信息失败:', err)
    // FastAPI 校验错误 detail 可能是数组，统一提取为可读消息
    let msg = '保存失败，请重试'
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') {
      msg = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      msg = detail.map((d: any) => d.msg || JSON.stringify(d)).join('；')
    } else if (err?.message) {
      msg = err.message
    }
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

// ========== 学科卡片数据 ==========
const subjects = ref<Array<{
  id: number
  name: string
  progress: number
  latestMsg: string
  recordMsg: string
  nextKnowledgePoint: string | null
  nextQuestionId: number | null
  nextReason: string | null
  newQuestionId: number | null
  recordQuestionId: number | null
  newRandomIndex: number
  recordRandomIndex: number
  newIdList: number[]
  recordIdList: number[]
}>>([])

const dailyQuestions = ref<DailyQuestion[]>([])

/** 截断题目描述，保留前 maxLen 个字符 */
const truncateDesc = (desc: string, maxLen: number = 28): string => {
  if (!desc) return '暂无记录'
  return desc.length > maxLen ? desc.slice(0, maxLen) + '...' : desc
}

onMounted(async () => {
  // 并行加载用户信息和学科列表
  await loadUserInfo()

  try {
    const [courses, progressMap, nextResult, dailyResult] = await Promise.all([
      fetchCourses(),
      fetchDashboardProgress(),
      fetchNextKnowledgePoints().catch((error) => {
        console.error('获取下一知识点推荐失败:', error)
        return null
      }),
      fetchDailyQuestion().catch((error) => {
        console.error('获取每日一题失败:', error)
        return null
      }),
    ])
    dailyQuestions.value = dailyResult || []
    if (courses && courses.length > 0) {
      // 先构建基础学科列表
      const baseSubjects = courses.map((course: Course) => {
        const recommendation = nextResult?.subjects.find((item) => item.course_id === course.course_id)
        // 学科进度取自 student_course_mastery.course_process（0~1），
        // 表中无该学科记录或进度为 0 时，一律默认为 0
        const rawProcess = progressMap[course.course_id]
        const progress = rawProcess != null ? Math.round(rawProcess * 100) : 0
        return {
          id: course.course_id,
          name: course.course_name,
          progress,
          latestMsg: '正在获取新题…',
          recordMsg: '正在获取做题记录…',
          nextKnowledgePoint: recommendation?.next_knowledge_point || null,
          nextQuestionId: recommendation?.next_question_id || null,
          nextReason: recommendation?.next_reason || null,
          newQuestionId: null as number | null,
          recordQuestionId: null as number | null,
          newRandomIndex: -1,
          recordRandomIndex: -1,
          newIdList: [] as number[],
          recordIdList: [] as number[],
        }
      })
      subjects.value = baseSubjects

      // 并行获取每个学科的随机题目
      const promises = baseSubjects.map(async (s) => {
        const [newResult, recordResult] = await Promise.allSettled([
          fetchDashboardNewQuestion(s.id),
          fetchDashboardRecordQuestion(s.id),
        ])

        if (newResult.status === 'fulfilled') {
          const newRes = newResult.value
          if (newRes.question) {
            s.newQuestionId = newRes.question.question_id
            s.newRandomIndex = newRes.random_index
            s.newIdList = newRes.id_list
            s.latestMsg = '【最新】' + truncateDesc(newRes.question.question_description)
          } else {
            s.latestMsg = '【最新】暂无新题'
          }
        } else {
          s.latestMsg = '【最新】暂时无法获取'
          console.error(`获取学科 ${s.name} 的最新题目失败:`, newResult.reason)
        }

        if (recordResult.status === 'fulfilled') {
          const recordRes = recordResult.value
          if (recordRes.question) {
            s.recordQuestionId = recordRes.question.question_id
            s.recordRandomIndex = recordRes.random_index
            s.recordIdList = recordRes.id_list
            s.recordMsg = '【巩固】' + truncateDesc(recordRes.question.question_description)
          } else {
            s.recordMsg = '【巩固】暂无记录'
          }
        } else {
          s.recordMsg = '【巩固】暂时无法获取'
          console.error(`获取学科 ${s.name} 的做题记录失败:`, recordResult.reason)
        }
      })
      await Promise.all(promises)
      // baseSubjects was assigned before the requests started. Re-assign a
      // fresh array after raw objects are updated so Vue tracks the results.
      subjects.value = [...baseSubjects]
    } else {
      subjects.value = []
    }
  } catch (error) {
    console.error('获取学科列表失败:', error)
    ElMessage.error('获取学科列表失败，请稍后重试')
    subjects.value = []
  }
})

// 路由跳转逻辑
const navigateTo = (path: string, subjectId?: number | string) => {
  router.push({
    path,
    query: subjectId ? { module: subjectId.toString() } : undefined
  })
}

/** 跳转到练习面板，携带随机题目 ID、随机索引和全量 ID 列表 */
const navigateToPractice = (subject: any, mode: 'new' | 'record') => {
  const questionId = mode === 'new' ? subject.newQuestionId : subject.recordQuestionId
  const randomIndex = mode === 'new' ? subject.newRandomIndex : subject.recordRandomIndex
  const idList = mode === 'new' ? subject.newIdList : subject.recordIdList
  if (!questionId) {
    ElMessage.warning('暂无可用题目')
    return
  }
  router.push({
    path: '/student/practice/panel',
    query: {
      questionId: String(questionId),
      module: String(subject.id),
      randomIndex: String(randomIndex),
      idList: idList.join(','),
    }
  })
}

const navigateToRecommendedPractice = (subject: any) => {
  if (!subject.nextQuestionId) {
    ElMessage.warning('暂无可用的下一步题目')
    return
  }
  router.push({
    path: '/student/practice/panel',
    query: {
      questionId: String(subject.nextQuestionId),
      module: String(subject.id),
    },
  })
}

const navigateToDailyQuestion = (question: DailyQuestion) => {
  router.push({
    path: '/student/practice/panel',
    query: {
      questionId: String(question.question_id),
      module: String(question.course_id),
    },
  })
}
</script>

<style scoped>
.daily-question-card {
  margin-bottom: 16px;
  border: 1px solid #b3d8ff;
  background: linear-gradient(135deg, rgba(236, 245, 255, 0.95), rgba(255, 255, 255, 0.75));
}

.daily-question-date {
  color: #909399;
  font-size: 0.75rem;
}

.daily-question-list {
  display: grid;
  gap: 10px;
}

.daily-question-item {
  padding: 10px 12px;
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.62);
}

.daily-question-item-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.daily-question-meta,
.daily-question-reason,
.daily-question-empty {
  margin: 0 0 8px;
  color: #606266;
  font-size: 0.8rem;
}

.daily-question-text {
  margin: 0 0 8px;
  color: #303133;
  font-size: 0.9rem;
  line-height: 1.6;
}

.daily-question-reason {
  color: #67c23a;
}

.next-step-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(240, 249, 235, 0.75);
}

.next-step-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.next-step-label {
  color: #67c23a;
  font-size: 0.75rem;
}

.next-step-copy strong {
  overflow: hidden;
  color: #303133;
  font-size: 0.85rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.dashboard-layout {
  display: flex;
  gap: 24px;
  padding: 24px;
  height: 100%;
}

/* 玻璃拟态卡片基础样式，沿用之前配好的 #e5e8e4 */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
}

.card-title {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
}

/* --- 左侧面板 --- */
.left-panel {
  flex: 0 0 320px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.personal-info .info-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-placeholder {
  font-size: 3rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-text p {
  margin: 8px 0;
  font-size: 0.95rem;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.rating-badge {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1;
}

/* --- AI 学习分析面板（替换原建议与评估） --- */
.ai-analysis-panel {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.analysis-scroll-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: 4px;
}

.analysis-scroll-area::-webkit-scrollbar {
  width: 4px;
}

.analysis-scroll-area::-webkit-scrollbar-thumb {
  background: #c0c5bd;
  border-radius: 2px;
}

.analysis-scroll-area::-webkit-scrollbar-track {
  background: transparent;
}

/* --- 右侧面板 --- */
.right-panel {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.subject-card {
  justify-content: space-between;
}

.subject-title {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  color: #2c3e50;
  font-weight: bold;
}

/* --- 核心需求：跑道进度条设计 --- */
.runway-container {
  position: relative;
  height: 40px;
  margin-bottom: 24px;
}

/* 横向的跑道 */
.runway-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: #a3a8a1;
  border-radius: 2px;
}

/* 终点标识容器 */
.finish-line {
  position: absolute;
  right: 0;
  bottom: 0;
  height: 24px;
  width: 20px;
}

/* 终点红色竖线 (旗杆) */
.flag-pole {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 2px;
  height: 24px;
  background-color: #f56c6c;
}

/* 终点红旗 (利用 clip-path 裁切成三角形) */
.flag-cloth {
  position: absolute;
  left: 2px;
  top: 0;
  width: 14px;
  height: 10px;
  background-color: #f56c6c;
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}

/* 进度条 */
.progress-bar {
  position: absolute;
  bottom: 0;
  font-size: 24px;
  line-height: 1;
  /* 平滑动画过渡 */
  transition: left 1s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 2;
  /* 增加立体阴影 */
  filter: drop-shadow(2px 2px 2px rgba(0, 0, 0, 0.2));
}

/* --- 操作列表 --- */
.action-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.action-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  border-radius: 8px;
}

.action-desc {
  font-size: 0.9rem;
  color: #555;
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.full-width-btn {
  width: 100%;
  margin-top: auto;
}

/* --- 个人信息卡片标题行 --- */
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-header-row .card-title {
  margin: 0;
}

/* --- 编辑弹窗表单 --- */
.edit-form {
  padding-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.analysis-idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 12px 0;
}

.analysis-desc {
  font-size: 0.9rem;
  color: #555;
  line-height: 1.6;
  margin: 0;
  text-align: center;
}

.analysis-trigger-btn {
  width: 100%;
  font-size: 1rem;
  padding: 14px 0;
  border-radius: 10px;
  letter-spacing: 1px;
}

/* --- 旋转加载特效 --- */
.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
}

.spinner-container {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.analysis-spinner {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 3px solid #c0c5bd;
  border-top-color: #409eff;
  animation: spin 0.8s linear infinite;
  z-index: 2;
}

.spinner-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid transparent;
  animation: spin 1.2s linear infinite;
}

.spinner-ring-1 {
  width: 48px;
  height: 48px;
  border-top-color: #67c23a;
  border-right-color: #67c23a;
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.spinner-ring-2 {
  width: 60px;
  height: 60px;
  border-bottom-color: #e6a23c;
  border-left-color: #e6a23c;
  animation-duration: 2s;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 0.95rem;
  color: #333;
  font-weight: 500;
  margin: 0;
}

.loading-subtext {
  font-size: 0.8rem;
  color: #888;
  margin: 0;
}

/* --- 分析结果展示 --- */
.analysis-result {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-rating-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 0;
}

.result-label {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.result-rating-badge {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
}

.dimension-indicators {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.dimension-tag {
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.dim-available {
  background: #e1f3d8;
  color: #67c23a;
  border: 1px solid #b3e19d;
}

.dim-missing {
  background: #f5f5f5;
  color: #aaa;
  border: 1px solid #e0e0e0;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-section {
  background: rgba(255, 255, 255, 0.4);
  border-radius: 8px;
  padding: 10px 14px;
}

.section-title {
  margin: 0 0 6px 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: #409eff;
}

.section-text {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.6;
  color: #444;
}

.priority-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.priority-chip {
  background: #ecf5ff;
  color: #409eff;
  font-size: 0.8rem;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid #d9ecff;
}

.reanalyze-btn {
  align-self: center;
  margin-top: 4px;
}

/* --- 分析出错状态 --- */
.analysis-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
}

.error-text {
  font-size: 0.85rem;
  color: #f56c6c;
  margin: 0;
  text-align: center;
}

/* --- 老师建议与评估 --- */
.teacher-section {
  margin-top: 8px;
}

.section-divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
  margin: 12px 0;
}

.teacher-title {
  margin: 0 0 8px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #e6a23c;
}

.ai-suggest-title {
  font-size: 1rem;
  color: #e6a23c;
}

.teacher-placeholder {
  margin: 0;
  font-size: 0.8rem;
  color: #999;
  font-style: italic;
}
</style>
