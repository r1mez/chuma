<template>
  <div class="assignment-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">TEACHING WORKSPACE</p>
        <h2>作业布置</h2>
        <p>从题库中选择题目，参考班级薄弱点和 DyGKT/RRF 推荐后发布作业。</p>
      </div>
      <el-tag type="success" effect="plain">真实题库与班级数据</el-tag>
    </section>

    <el-card shadow="never" class="filter-card">
      <el-form inline>
        <el-form-item label="学科">
          <el-select v-model="selectedCourseId" placeholder="选择学科" clearable @change="handleCourseChange">
            <el-option
              v-for="course in courses"
              :key="course.course_id"
              :label="course.course_name"
              :value="course.course_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="selectedClassId" placeholder="选择班级" clearable>
            <el-option
              v-for="classItem in classes"
              :key="classItem.class_id"
              :label="classItem.class_name"
              :value="classItem.class_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="recommendationLoading"
            :disabled="!selectedCourseId || !selectedClassId"
            @click="loadRecommendations"
          >
            获取班级推荐
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button :disabled="!selectedCourseId" @click="loadQuestionBank">刷新题库</el-button>
        </el-form-item>
      </el-form>
      <p class="filter-tip">推荐会融合班级错题知识点、未做比例，以及已有 DyGKT/RRF 个体推荐；最终题目仍由教师确认。</p>
    </el-card>

    <div class="content-grid">
      <el-card shadow="never" class="question-card">
        <template #header>
          <div class="card-header">
            <span>题库选择</span>
            <div class="header-actions">
              <el-input v-model="questionSearch" clearable placeholder="搜索题干/知识点" style="width: 220px" />
              <el-tag type="info">已选 {{ selectedQuestions.length }} 题</el-tag>
            </div>
          </div>
        </template>
        <el-table
          ref="questionTableRef"
          v-loading="questionLoading"
          :data="filteredQuestions"
          row-key="question_id"
          height="470"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column label="题目" min-width="300">
            <template #default="scope">
              <div class="question-title">{{ scope.row.question_description }}</div>
              <div class="question-meta">
                <span>{{ scope.row.kg_node_name || '未标注知识点' }}</span>
                <span>{{ questionTypeLabel(scope.row.question_type) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="难度" width="72">
            <template #default="scope">{{ scope.row.question_difficulty }}/5</template>
          </el-table-column>
          <el-table-column label="推荐" width="120">
            <template #default="scope">
              <el-tag v-if="recommendationMap.has(scope.row.question_id)" type="warning" size="small">
                {{ recommendationMap.get(scope.row.question_id)?.recommendation_source === 'tgnn_rrf' ? 'DyGKT/RRF' : '班级薄弱点' }}
              </el-tag>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="推荐理由" min-width="220">
            <template #default="scope">
              <span class="reason">{{ recommendationMap.get(scope.row.question_id)?.recommendation_reason || '可手动选择' }}</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!questionLoading && filteredQuestions.length === 0" description="暂无题库题目" />
      </el-card>

      <el-card shadow="never" class="publish-card">
        <template #header><span>发布作业</span></template>
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="作业名称" required>
            <el-input v-model="form.title" maxlength="128" show-word-limit placeholder="例如：数据结构第二章巩固练习" />
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="form.description" type="textarea" :rows="4" maxlength="4000" placeholder="给学生的作业说明（可选）" />
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker
              v-model="form.dueAt"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="不设置截止时间"
              style="width: 100%"
            />
          </el-form-item>
          <div class="selected-summary">
            <strong>{{ selectedQuestions.length }} 道题</strong>
            <span v-if="selectedCourseName && selectedClassName">将发布到 {{ selectedClassName }} · {{ selectedCourseName }}</span>
            <span v-else>请先选择班级、学科和题目</span>
          </div>
          <el-button type="primary" size="large" :loading="publishing" :disabled="!canPublish" @click="publishAssignment" class="publish-button">
            发布作业
          </el-button>
        </el-form>
      </el-card>
    </div>

    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <span>已发布作业</span>
          <el-button text type="primary" @click="loadAssignments">刷新</el-button>
        </div>
      </template>
      <el-table v-loading="assignmentLoading" :data="assignments" stripe>
        <el-table-column prop="title" label="作业" min-width="220" />
        <el-table-column prop="course_name" label="学科" width="140" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column prop="question_count" label="题数" width="80" />
        <el-table-column label="截止时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.due_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openResults(scope.row.assignment_id)">查看结果</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!assignmentLoading && assignments.length === 0" description="还没有发布作业" />
    </el-card>

    <el-dialog v-model="resultsVisible" title="作业完成情况" width="860px">
      <template v-if="results">
        <div class="result-summary">
          <div><strong>{{ results.assignment.title }}</strong><span>{{ results.assignment.course_name }} · {{ results.assignment.class_name }}</span></div>
          <div class="summary-metrics">
            <span>完成率 <b>{{ results.summary.completion_rate }}%</b></span>
            <span>班级平均分 <b>{{ results.summary.average_score ?? '—' }}</b></span>
            <span>已提交 <b>{{ results.summary.submitted_student_count }}/{{ results.summary.student_count }}</b></span>
          </div>
        </div>
        <el-table :data="results.students" max-height="430" stripe>
          <el-table-column prop="stu_name" label="学生" width="150" />
          <el-table-column label="完成进度" width="150">
            <template #default="scope">{{ scope.row.submitted_count }}/{{ scope.row.total_questions }}（{{ scope.row.completion_rate }}%）</template>
          </el-table-column>
          <el-table-column label="平均分" width="100">
            <template #default="scope">{{ scope.row.average_score ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="正确率" width="100">
            <template #default="scope">{{ scope.row.accuracy == null ? '—' : `${scope.row.accuracy}%` }}</template>
          </el-table-column>
          <el-table-column label="最近提交" min-width="160">
            <template #default="scope">{{ formatDate(scope.row.latest_submitted_at) }}</template>
          </el-table-column>
        </el-table>
      </template>
      <el-empty v-else description="暂无结果" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchQuestions, type Question } from '@/api/practice'
import { getTeacherClasses, getTeacherCourses, type TeacherClass, type TeacherCourse } from '@/api/teacher'
import {
  createAssignment,
  fetchAssignmentRecommendations,
  fetchAssignmentResults,
  fetchTeacherAssignments,
  type AssignmentItem,
  type AssignmentRecommendation,
  type AssignmentResults,
} from '@/api/assignments'

const courses = ref<TeacherCourse[]>([])
const classes = ref<TeacherClass[]>([])
const assignments = ref<AssignmentItem[]>([])
const questions = ref<Question[]>([])
const recommendations = ref<AssignmentRecommendation[]>([])
const selectedQuestions = ref<Question[]>([])
const questionTableRef = ref<any>(null)
const selectedCourseId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const questionSearch = ref('')
const questionLoading = ref(false)
const recommendationLoading = ref(false)
const assignmentLoading = ref(false)
const publishing = ref(false)
const resultsVisible = ref(false)
const results = ref<AssignmentResults | null>(null)
const form = reactive({ title: '', description: '', dueAt: '' as string | null })

const selectedCourseName = computed(() => courses.value.find(item => item.course_id === selectedCourseId.value)?.course_name)
const selectedClassName = computed(() => classes.value.find(item => item.class_id === selectedClassId.value)?.class_name)
const recommendationMap = computed(() => new Map(recommendations.value.map(item => [item.question_id, item])))
const filteredQuestions = computed(() => {
  const keyword = questionSearch.value.trim().toLowerCase()
  if (!keyword) return questions.value
  return questions.value.filter(item => `${item.question_description} ${item.kg_node_name || ''}`.toLowerCase().includes(keyword))
})
const canPublish = computed(() => Boolean(form.title.trim() && selectedCourseId.value && selectedClassId.value && selectedQuestions.value.length))

const questionTypeLabel = (type: string) => ({
  single_choice: '单选题', choice: '单选题', multiple_choice: '多选题',
  true_false: '判断题', T_or_F: '判断题', fill_blanks: '填空题',
  Fill_blanks: '填空题', fill_Blanks: '填空题', Q_A: '简答题', q_a: '简答题',
}[type] || type)

const formatDate = (value?: string | null) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'

const loadQuestionBank = async () => {
  if (!selectedCourseId.value) {
    questions.value = []
    return
  }
  questionLoading.value = true
  try {
    questions.value = await fetchQuestions(selectedCourseId.value)
    selectedQuestions.value = []
    recommendations.value = []
  } catch {
    ElMessage.error('题库加载失败')
  } finally {
    questionLoading.value = false
  }
}

const handleCourseChange = async () => {
  await loadQuestionBank()
  recommendations.value = []
}

const handleSelectionChange = (rows: Question[]) => {
  selectedQuestions.value = rows
}

const loadRecommendations = async () => {
  if (!selectedCourseId.value || !selectedClassId.value) return
  recommendationLoading.value = true
  try {
    if (!questions.value.length) await loadQuestionBank()
    recommendations.value = await fetchAssignmentRecommendations(selectedClassId.value, selectedCourseId.value)
    const topIds = new Set(recommendations.value.slice(0, 5).map(item => item.question_id))
    selectedQuestions.value = questions.value.filter(item => topIds.has(item.question_id))
    await nextTick()
    questionTableRef.value?.clearSelection()
    selectedQuestions.value.forEach(item => questionTableRef.value?.toggleRowSelection(item, true))
    ElMessage.success(`已载入 ${recommendations.value.length} 道推荐题，并预选前 ${selectedQuestions.value.length} 道`)
  } catch {
    ElMessage.error('班级推荐加载失败，请检查 AI 服务或直接从题库选择')
  } finally {
    recommendationLoading.value = false
  }
}

const loadAssignments = async () => {
  assignmentLoading.value = true
  try {
    assignments.value = await fetchTeacherAssignments()
  } catch {
    ElMessage.error('作业列表加载失败')
  } finally {
    assignmentLoading.value = false
  }
}

const publishAssignment = async () => {
  if (!canPublish.value || !selectedCourseId.value || !selectedClassId.value) return
  publishing.value = true
  try {
    const metadata = recommendationMap.value
    await createAssignment({
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      class_id: selectedClassId.value,
      course_id: selectedCourseId.value,
      due_at: form.dueAt || null,
      questions: selectedQuestions.value.map((question, index) => {
        const recommendation = metadata.get(question.question_id)
        return {
          question_id: question.question_id,
          sort_order: index,
          priority_score: recommendation?.priority_score,
          recommendation_source: recommendation?.recommendation_source,
          recommendation_reason: recommendation?.recommendation_reason,
        }
      }),
    })
    ElMessage.success('作业发布成功')
    form.title = ''
    form.description = ''
    form.dueAt = null
    selectedQuestions.value = []
    questionTableRef.value?.clearSelection()
    await loadAssignments()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '作业发布失败')
  } finally {
    publishing.value = false
  }
}

const openResults = async (assignmentId: number) => {
  resultsVisible.value = true
  results.value = null
  try {
    results.value = await fetchAssignmentResults(assignmentId)
  } catch {
    ElMessage.error('作业结果加载失败')
  }
}

onMounted(async () => {
  try {
    const [courseData, classData] = await Promise.all([getTeacherCourses(), getTeacherClasses()])
    courses.value = courseData
    classes.value = classData
    await loadAssignments()
  } catch {
    ElMessage.error('教师数据加载失败')
  }
})
</script>

<style scoped>
.assignment-page { display: flex; flex-direction: column; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.page-heading h2 { margin: 3px 0 6px; color: #17243c; font-size: 25px; }
.page-heading p:not(.eyebrow) { margin: 0; color: #718096; font-size: 13px; }
.eyebrow { margin: 0; color: #2d5ac0; font-size: 11px; font-weight: 700; letter-spacing: .12em; }
.filter-card, .question-card, .publish-card, .history-card { border-color: #e2e8f0; border-radius: 14px; }
.filter-card :deep(.el-card__body) { padding-bottom: 10px; }
.filter-tip { margin: -4px 0 0; color: #8b97a9; font-size: 12px; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(300px, .8fr); gap: 18px; align-items: start; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 14px; color: #27364f; font-weight: 700; }
.header-actions { display: flex; align-items: center; gap: 12px; }
.question-title { overflow: hidden; color: #344054; text-overflow: ellipsis; white-space: nowrap; }
.question-meta { display: flex; gap: 10px; margin-top: 5px; color: #98a2b3; font-size: 12px; }
.muted { color: #c0c7d1; }
.reason { color: #667085; font-size: 12px; line-height: 1.45; }
.selected-summary { display: flex; flex-direction: column; gap: 5px; margin: 12px 0 18px; padding: 12px; color: #667085; background: #f7f9fc; border-radius: 10px; font-size: 12px; }
.selected-summary strong { color: #2d5ac0; font-size: 20px; }
.publish-button { width: 100%; }
.result-summary { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 16px; padding: 14px 16px; background: #f7f9fc; border-radius: 10px; }
.result-summary > div:first-child { display: flex; flex-direction: column; gap: 5px; }
.result-summary span { color: #8b97a9; font-size: 12px; }
.summary-metrics { display: flex; gap: 18px; color: #667085; font-size: 12px; }
.summary-metrics b { margin-left: 4px; color: #2d5ac0; font-size: 16px; }
@media (max-width: 960px) { .content-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .page-heading, .result-summary { flex-direction: column; align-items: flex-start; } .header-actions { flex-wrap: wrap; } .summary-metrics { flex-wrap: wrap; } }
</style>
