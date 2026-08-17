<template>
  <div class="lesson-plan-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">AI TEACHING STUDIO</p>
        <h2>教案生成</h2>
        <p>基于课程知识图谱、教材资料和班级真实学情生成可交互的 HTML 课堂课件，并保留 PPTX 导出。</p>
      </div>
      <el-tag type="success" effect="plain" class="source-tag">
        <BookOpen :size="14" aria-hidden="true" /> 可追溯知识来源
      </el-tag>
    </section>

    <el-card shadow="never" class="create-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>创建一份课堂教案</span>
            <small>选择授课范围后，先由 Agent 生成结构化提纲，再渲染为 PPTX。</small>
          </div>
          <el-tag type="info" effect="plain">异步生成</el-tag>
        </div>
      </template>

      <el-form class="creation-form" label-position="top" @submit.prevent>
        <el-form-item label="授课学科" required>
          <el-select
            v-model="selectedCourseId"
            placeholder="选择你教授的学科"
            clearable
            :loading="courseLoading"
            @change="handleCourseChange"
          >
            <el-option v-for="course in courses" :key="course.course_id" :label="course.course_name" :value="course.course_id" />
          </el-select>
        </el-form-item>

        <el-form-item label="授课班级" required>
          <el-select v-model="selectedClassId" placeholder="选择授课班级" clearable @change="refreshClassContext">
            <el-option v-for="classItem in classes" :key="classItem.class_id" :label="classItem.class_name" :value="classItem.class_id" />
          </el-select>
        </el-form-item>

        <el-form-item label="本节小节" required>
          <el-select
            v-model="selectedSectionId"
            placeholder="先选择学科，再选择具体章节或小节"
            clearable
            filterable
            :loading="sectionLoading"
            :disabled="!selectedCourseId"
          >
            <el-option
              v-for="section in sections"
              :key="section.id"
              :label="section.path"
              :value="section.id"
            >
              <div class="section-option">
                <span>{{ section.path }}</span>
                <small>{{ section.type === 'Chapter' ? '章节/小节' : section.type }}</small>
              </div>
            </el-option>
          </el-select>
          <p v-if="selectedSection?.description" class="field-helper">{{ selectedSection.description }}</p>
          <p v-else-if="selectedCourseId && !sectionLoading && sections.length === 0" class="field-helper warning">该学科尚未建立可选的章节层级图谱。</p>
        </el-form-item>

        <el-form-item label="课件主题" required>
          <el-select v-model="selectedThemePack" :disabled="generating" filterable>
            <el-option v-for="theme in themeOptions" :key="theme.value" :label="theme.label" :value="theme.value">
              <div class="theme-option"><span>{{ theme.label }}</span><small>{{ theme.description }}</small></div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="课件页数" required>
          <el-select v-model="slideCount" :disabled="generating">
            <el-option v-for="count in slideCounts" :key="count" :label="`${count} 页`" :value="count" />
          </el-select>
        </el-form-item>

        <div class="review-control">
          <div>
            <strong>加入上一节学情回顾</strong>
            <p>根据上一小节和班级掌握情况生成回顾页；至少需要 8 页课件。</p>
          </div>
          <el-switch v-model="includeReview" aria-label="加入上一节学情回顾" :disabled="generating" />
        </div>

        <div class="generation-action">
          <el-button
            type="primary"
            size="large"
            class="generate-button"
            :loading="generating"
            :disabled="!canGenerate"
            @click="generateLessonPlan"
          >
            <Sparkles :size="18" aria-hidden="true" />
            {{ generating ? '正在提交生成任务…' : '生成 PPT 教案' }}
          </el-button>
            <p>生成后可先打开浏览器课堂预览，再下载可编辑 PPTX。</p>
        </div>
      </el-form>
    </el-card>

    <section class="context-grid" aria-label="当前班级学情摘要">
      <el-card shadow="never" class="context-card">
        <template #header>
          <div class="card-header compact"><span>班级学习概览</span><el-button link type="primary" :disabled="!canLoadContext" @click="refreshClassContext">刷新</el-button></div>
        </template>
        <template v-if="contextLoading">
          <el-skeleton :rows="3" animated />
        </template>
        <template v-else-if="classSummary?.status === 'ok'">
          <div class="metrics-row">
            <div><span>学生数</span><strong>{{ classSummary.student_count ?? '—' }}</strong></div>
            <div><span>平均掌握度</span><strong>{{ formatPercent(classSummary.average_mastery) }}</strong></div>
            <div><span>近期平均分</span><strong>{{ classSummary.latest_average_score ?? '—' }}</strong></div>
          </div>
          <p class="context-note">这些真实班级数据会作为教案的教学节奏与回顾依据。</p>
        </template>
        <el-empty v-else :image-size="52" description="选择班级与学科后显示学情摘要" />
      </el-card>

      <el-card shadow="never" class="context-card">
        <template #header><div class="card-header compact"><span>优先关注的易错知识点</span><span class="muted-label">来自班级错题聚合</span></div></template>
        <template v-if="contextLoading"><el-skeleton :rows="3" animated /></template>
        <div v-else-if="difficultKnowledge.length" class="difficulty-list">
          <div v-for="item in difficultKnowledge.slice(0, 4)" :key="item.name" class="difficulty-item">
            <span>{{ item.name }}</span>
            <el-progress :percentage="Math.round(item.ratio * 100)" :stroke-width="7" :show-text="false" />
            <small>{{ item.count }} 次错题</small>
          </div>
        </div>
        <el-empty v-else :image-size="52" description="暂无可用的错题聚合数据" />
      </el-card>
    </section>

    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>已生成教案</span>
            <small>生成过程与文件状态会自动更新。</small>
          </div>
          <el-button :loading="historyLoading" text type="primary" @click="loadPlans"><RefreshCw :size="15" aria-hidden="true" /> 刷新</el-button>
        </div>
      </template>

      <el-table v-loading="historyLoading" :data="plans" row-key="lesson_plan_id" class="plan-table">
        <el-table-column label="教案" min-width="260">
          <template #default="scope">
            <div class="plan-title">
              <Presentation :size="17" aria-hidden="true" />
              <div><strong>{{ scope.row.title }}</strong><small>{{ scope.row.section_path }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="班级 / 学科" min-width="170">
          <template #default="scope"><span>{{ scope.row.class_name || '—' }} · {{ scope.row.course_name || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="页数" width="80" align="center"><template #default="scope">{{ scope.row.slide_count }}</template></el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope"><el-tag :type="statusTagType(scope.row.status)" effect="plain">{{ statusText(scope.row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="创建时间" width="174"><template #default="scope">{{ formatDate(scope.row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :disabled="scope.row.status !== 'completed'" @click="openOutline(scope.row)">查看提纲</el-button>
            <el-button link type="success" :disabled="scope.row.status !== 'completed'" @click="previewHtml(scope.row)">课堂预览</el-button>
            <el-button link type="primary" :loading="downloadingId === scope.row.lesson_plan_id" :disabled="scope.row.status !== 'completed'" @click="download(scope.row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!historyLoading && plans.length === 0" :image-size="70" description="还没有生成过教案" />
    </el-card>

    <el-dialog v-model="outlineVisible" :title="activePlan?.title || '教案提纲'" width="min(920px, calc(100vw - 32px))" destroy-on-close>
      <template v-if="activePlan?.content">
        <div class="outline-summary">
          <FileText :size="20" aria-hidden="true" />
          <p>{{ activePlan.content.summary || '已完成结构化教案生成。' }}</p>
          <el-tag v-if="activePlan.content.review_inserted" type="warning" effect="plain">含上一节回顾</el-tag>
        </div>
        <ol class="slide-outline">
          <li v-for="(slide, index) in activePlan.content.slides" :key="`${slide.title}-${index}`">
            <span class="slide-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <div>
              <div class="slide-heading"><strong>{{ slide.title }}</strong><el-tag size="small" effect="plain">{{ layoutText(slide.layout) }}</el-tag></div>
              <p v-if="slide.takeaway" class="slide-takeaway">{{ slide.takeaway }}</p>
              <ul v-if="slide.bullets.length"><li v-for="bullet in slide.bullets" :key="bullet">{{ bullet }}</li></ul>
              <div v-if="slide.blocks?.length" class="slide-blocks">
                <span v-for="(block, blockIndex) in slide.blocks" :key="`${block.type}-${blockIndex}`" class="slide-block-chip">
                  {{ blockLabel(block) }}
                </span>
              </div>
              <div v-if="slide.diagram_nodes?.length" class="slide-diagram-nodes">图谱节点：{{ slide.diagram_nodes.join(' · ') }}</div>
              <small v-if="slide.source_refs.length">依据：{{ slide.source_refs.join(' · ') }}</small>
            </div>
          </li>
        </ol>
      </template>
      <el-empty v-else description="该教案尚未生成可预览的提纲" />
      <template #footer>
        <el-button @click="outlineVisible = false">关闭</el-button>
        <el-button v-if="activePlan?.status === 'completed'" type="success" @click="previewHtml(activePlan)">课堂预览</el-button>
        <el-button v-if="activePlan?.status === 'completed'" type="primary" @click="download(activePlan)"><Download :size="16" aria-hidden="true" /> 下载 PPTX</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { BookOpen, Download, FileText, Presentation, RefreshCw, Sparkles } from 'lucide-vue-next'
import { getClassSummary, getDifficultKnowledge, getTeacherClasses, getTeacherCourses, type ClassSummary, type DifficultKnowledgePoint, type TeacherClass, type TeacherCourse } from '@/api/teacher'
import { createLessonPlan, downloadLessonPlan, getCourseSections, getLessonPlan, getLessonPlanPreviewTicket, getLessonPlans, type CourseSection, type LessonPlanBlock, type LessonPlanItem, type LessonPlanStatus, type ThemePack } from '@/api/lessonPlans'

const courses = ref<TeacherCourse[]>([])
const classes = ref<TeacherClass[]>([])
const sections = ref<CourseSection[]>([])
const plans = ref<LessonPlanItem[]>([])
const selectedCourseId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const selectedSectionId = ref<string | null>(null)
const includeReview = ref(true)
const slideCount = ref(10)
const selectedThemePack = ref<ThemePack>('theme03')
const courseLoading = ref(false)
const sectionLoading = ref(false)
const contextLoading = ref(false)
const historyLoading = ref(false)
const generating = ref(false)
const downloadingId = ref<number | null>(null)
const classSummary = ref<ClassSummary | null>(null)
const difficultKnowledge = ref<DifficultKnowledgePoint[]>([])
const outlineVisible = ref(false)
const activePlan = ref<LessonPlanItem | null>(null)
let pollingTimer: ReturnType<typeof window.setInterval> | undefined

const slideCounts = Array.from({ length: 10 }, (_, index) => index + 7)
const themeOptions: Array<{ value: ThemePack; label: string; description: string }> = [
  { value: 'theme01', label: 'theme01 · 轻拟态风', description: '产品介绍 / 企业汇报' },
  { value: 'theme02', label: 'theme02 · 炫光紫绿风', description: '科技发布 / AI 主题' },
  { value: 'theme03', label: 'theme03 · 深浅代码风', description: '计算机课程 / 技术讲解' },
  { value: 'theme04', label: 'theme04 · 玻璃糖果风', description: '年轻化 / 创意提案' },
  { value: 'theme05', label: 'theme05 · 色谱图表风', description: '数据报告 / 分析' },
  { value: 'theme06', label: 'theme06 · 深色图谱风', description: '知识结构 / 系统分析' },
  { value: 'theme07', label: 'theme07 · 冷白调研风', description: '教材讲解 / 学术表达' },
  { value: 'theme08', label: 'theme08 · 黑金实验风', description: '实验性 / 高端发布' },
  { value: 'theme09', label: 'theme09 · 深蓝杂志风', description: '专题故事 / 深度内容' },
  { value: 'theme10', label: 'theme10 · 金色指数风', description: '指数 / 榜单 / 金融数据' },
  { value: 'theme11', label: 'theme11 · 高能增长风', description: '复盘 / 方案 / 路演' },
  { value: 'theme12', label: 'theme12 · 声波霓虹风', description: '潮流活动 / 娱乐主题' },
]
const selectedSection = computed(() => sections.value.find(item => item.id === selectedSectionId.value) || null)
const canLoadContext = computed(() => Boolean(selectedCourseId.value && selectedClassId.value))
const canGenerate = computed(() => Boolean(selectedCourseId.value && selectedClassId.value && selectedSectionId.value && (!includeReview.value || slideCount.value >= 8)))
const hasActivePlans = computed(() => plans.value.some(plan => plan.status === 'queued' || plan.status === 'generating'))

watch(includeReview, (enabled) => {
  if (enabled && slideCount.value < 8) slideCount.value = 8
})

function statusText(status: LessonPlanStatus) {
  return { queued: '等待生成', generating: '正在生成', completed: '已完成', failed: '生成失败' }[status]
}

function statusTagType(status: LessonPlanStatus) {
  return { queued: 'info', generating: 'warning', completed: 'success', failed: 'danger' }[status] as 'info' | 'warning' | 'success' | 'danger'
}

function layoutText(layout: string) {
  return ({ title: '标题页', objectives: '学习目标', review: '课堂回顾', knowledge_map: '图谱定位', concept: '核心概念', comparison: '概念对比', example: '例题演示', difficulty_focus: '易错点', activity: '课堂活动', summary: '小结' } as Record<string, string>)[layout] || '内容页'
}

function blockLabel(block: LessonPlanBlock) {
  const labels: Record<string, string> = {
    highlight: '核心判断',
    text: '支撑要点',
    comparison: '左右对比',
    process: '步骤流程',
    question: '课堂问题',
    code: '代码示例',
    table: '数据表格',
  }
  return labels[block.type] || '内容块'
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function formatPercent(value?: number | null) {
  return value == null ? '—' : `${Math.round(value)}%`
}

async function loadSections() {
  if (!selectedCourseId.value) {
    sections.value = []
    return
  }
  sectionLoading.value = true
  try {
    sections.value = await getCourseSections(selectedCourseId.value)
  } catch {
    sections.value = []
    ElMessage.error('小节列表加载失败，请检查知识图谱服务')
  } finally {
    sectionLoading.value = false
  }
}

async function handleCourseChange() {
  selectedSectionId.value = null
  classSummary.value = null
  difficultKnowledge.value = []
  await Promise.all([loadSections(), refreshClassContext()])
}

async function refreshClassContext() {
  if (!canLoadContext.value || !selectedCourseId.value || !selectedClassId.value) {
    classSummary.value = null
    difficultKnowledge.value = []
    return
  }
  contextLoading.value = true
  try {
    const [summary, difficult] = await Promise.all([
      getClassSummary(selectedClassId.value, selectedCourseId.value),
      getDifficultKnowledge(selectedClassId.value, selectedCourseId.value),
    ])
    classSummary.value = summary
    difficultKnowledge.value = difficult
  } catch {
    classSummary.value = null
    difficultKnowledge.value = []
    ElMessage.warning('班级学情暂时不可用，仍可生成基于知识图谱的教案')
  } finally {
    contextLoading.value = false
  }
}

async function loadPlans(silent = false) {
  if (!silent) historyLoading.value = true
  try {
    plans.value = await getLessonPlans()
  } catch {
    if (!silent) ElMessage.error('教案列表加载失败')
  } finally {
    if (!silent) historyLoading.value = false
    syncPolling()
  }
}

function syncPolling() {
  if (hasActivePlans.value && !pollingTimer) {
    pollingTimer = window.setInterval(() => { void loadPlans(true) }, 3500)
  } else if (!hasActivePlans.value && pollingTimer) {
    window.clearInterval(pollingTimer)
    pollingTimer = undefined
  }
}

async function generateLessonPlan() {
  if (!canGenerate.value || !selectedCourseId.value || !selectedClassId.value || !selectedSectionId.value) return
  generating.value = true
  try {
    const plan = await createLessonPlan({
      course_id: selectedCourseId.value,
      class_id: selectedClassId.value,
      section_id: selectedSectionId.value,
      include_review: includeReview.value,
      slide_count: slideCount.value,
      theme_pack: selectedThemePack.value,
    })
    plans.value = [plan, ...plans.value.filter(item => item.lesson_plan_id !== plan.lesson_plan_id)]
    ElMessage.success('教案任务已提交，完成后可打开 HTML 课堂预览或下载 PPTX')
    syncPolling()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '教案任务提交失败')
  } finally {
    generating.value = false
  }
}

async function openOutline(plan: LessonPlanItem) {
  activePlan.value = plan
  outlineVisible.value = true
  if (plan.content) return
  try {
    const latest = await getLessonPlan(plan.lesson_plan_id)
    activePlan.value = latest
    plans.value = plans.value.map(item => item.lesson_plan_id === latest.lesson_plan_id ? latest : item)
  } catch {
    ElMessage.error('教案提纲加载失败')
  }
}

async function download(plan: LessonPlanItem) {
  downloadingId.value = plan.lesson_plan_id
  try {
    const blob = await downloadLessonPlan(plan.lesson_plan_id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = plan.file_name || `${plan.title}.pptx`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || 'PPTX 下载失败')
  } finally {
    downloadingId.value = null
  }
}

async function previewHtml(plan: LessonPlanItem) {
  const previewWindow = window.open('', '_blank')
  try {
    const ticket = await getLessonPlanPreviewTicket(plan.lesson_plan_id)
    if (previewWindow) {
      previewWindow.location.href = ticket.url
    } else {
      ElMessage.warning('浏览器拦截了新窗口，请允许本站打开课堂预览')
    }
  } catch (error: any) {
    previewWindow?.close()
    ElMessage.error(error?.response?.data?.detail || 'HTML 课堂预览打开失败')
  }
}

onMounted(async () => {
  courseLoading.value = true
  try {
    const [courseData, classData] = await Promise.all([getTeacherCourses(), getTeacherClasses()])
    courses.value = courseData
    classes.value = classData
  } catch {
    ElMessage.error('教师基础数据加载失败')
  } finally {
    courseLoading.value = false
  }
  await loadPlans()
})

onUnmounted(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
})
</script>

<style scoped>
.lesson-plan-page { display: flex; flex-direction: column; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.page-heading h2 { margin: 3px 0 6px; color: #17243c; font-size: 25px; letter-spacing: -.02em; }
.page-heading p:not(.eyebrow) { margin: 0; color: #718096; font-size: 13px; line-height: 1.6; }
.eyebrow { margin: 0; color: #2d5ac0; font-size: 11px; font-weight: 700; letter-spacing: .12em; }
.source-tag { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.create-card, .context-card, .history-card { border-color: #e2e8f0; border-radius: 14px; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; color: #27364f; font-weight: 700; }
.card-header > div { display: flex; flex-direction: column; gap: 4px; }
.card-header small { color: #8b97a9; font-size: 12px; font-weight: 400; }
.card-header.compact { font-size: 14px; }
.muted-label { color: #98a2b3; font-size: 11px; font-weight: 400; }
.creation-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 18px; }
.creation-form :deep(.el-select) { width: 100%; }
.field-helper { grid-column: 1 / -1; margin: -10px 0 5px; color: #718096; font-size: 12px; line-height: 1.5; }
.field-helper.warning { color: #b45309; }
.section-option { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.theme-option { display: flex; align-items: center; justify-content: space-between; gap: 16px; width: 100%; }
.theme-option small { color: #7b879c; }
.section-option small { color: #98a2b3; font-size: 11px; }
.review-control { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 15px 16px; border: 1px solid #dbeafe; border-radius: 11px; background: #f8fbff; }
.review-control strong { color: #27364f; font-size: 14px; }
.review-control p { margin: 5px 0 0; color: #718096; font-size: 12px; line-height: 1.5; }
.generation-action { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; margin-top: 4px; }
.generate-button { min-width: 184px; }
.generate-button :deep(span) { display: inline-flex; align-items: center; gap: 7px; }
.generation-action p { margin: 0; color: #8b97a9; font-size: 12px; }
.context-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.metrics-row > div { display: flex; flex-direction: column; gap: 7px; padding: 8px 10px; border-radius: 9px; background: #f8fafc; }
.metrics-row span { color: #7a8699; font-size: 11px; }
.metrics-row strong { color: #2d5ac0; font-size: 20px; font-variant-numeric: tabular-nums; }
.context-note { margin: 13px 0 0; color: #8b97a9; font-size: 12px; line-height: 1.55; }
.difficulty-list { display: flex; flex-direction: column; gap: 12px; }
.difficulty-item { display: grid; grid-template-columns: minmax(90px, 1fr) minmax(80px, 1.4fr) auto; align-items: center; gap: 10px; }
.difficulty-item span { overflow: hidden; color: #475467; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.difficulty-item small { color: #98a2b3; font-size: 11px; white-space: nowrap; }
.plan-table :deep(.el-table__cell) { padding-top: 12px; padding-bottom: 12px; }
.plan-title { display: flex; align-items: flex-start; gap: 10px; color: #2d5ac0; }
.plan-title > div { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.plan-title strong { overflow: hidden; color: #344054; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.plan-title small { overflow: hidden; color: #98a2b3; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.outline-summary { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 18px; padding: 13px 14px; border-radius: 10px; color: #475467; background: #f7f9fc; }
.outline-summary > p { flex: 1; margin: 0; font-size: 13px; line-height: 1.55; }
.slide-outline { display: flex; flex-direction: column; gap: 14px; margin: 0; padding: 0; list-style: none; }
.slide-outline > li { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 12px; }
.slide-number { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 8px; color: #2d5ac0; background: #eef4ff; font-size: 11px; font-weight: 700; }
.slide-heading { display: flex; align-items: center; gap: 9px; color: #344054; }
.slide-heading strong { font-size: 14px; }
.slide-takeaway { margin: 6px 0 0; color: #475467; font-size: 12px; line-height: 1.5; }
.slide-blocks { display: flex; flex-wrap: wrap; gap: 5px; margin: 7px 0 3px; }
.slide-block-chip { padding: 2px 7px; border: 1px solid #dbeafe; border-radius: 999px; color: #2d5ac0; background: #f8fbff; font-size: 11px; }
.slide-outline ul { display: flex; flex-direction: column; gap: 4px; margin: 8px 0; padding-left: 18px; color: #667085; font-size: 13px; line-height: 1.5; }
.slide-diagram-nodes { margin: 6px 0; color: #667085; font-size: 12px; line-height: 1.45; }
.slide-outline small { color: #98a2b3; font-size: 11px; line-height: 1.45; }
@media (max-width: 960px) { .creation-form, .context-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .page-heading, .generation-action, .review-control { flex-direction: column; align-items: flex-start; } .generate-button { width: 100%; } .metrics-row { grid-template-columns: 1fr; } .difficulty-item { grid-template-columns: 1fr; gap: 5px; } }
</style>
