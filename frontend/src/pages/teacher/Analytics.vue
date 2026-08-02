<template>
  <div class="teacher-page flex h-full flex-col gap-6 p-4">
    <div class="flex min-h-[300px] gap-6 max-lg:flex-col">
      <el-card class="teacher-card w-1/4 max-lg:w-full" shadow="never">
        <template #header>
          <div class="flex gap-3 max-sm:flex-col">
            <el-select v-model="selectedClass" placeholder="选择班级" class="flex-1">
              <el-option
                v-for="cls in classList"
                :key="cls.class_id"
                :label="cls.class_name"
                :value="cls.class_id"
              />
            </el-select>
            <el-select v-model="selectedCourse" placeholder="选择学科" class="flex-1">
              <el-option
                v-for="course in courseList"
                :key="course.course_id"
                :label="course.course_name"
                :value="course.course_id"
              />
            </el-select>
          </div>
        </template>

        <div class="space-y-4 text-sm text-slate-700">
          <div class="flex items-center justify-between">
            <span>学生数量</span>
            <span class="font-semibold text-slate-900">{{ currentClassStudentCount }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span>班级 AI 评级</span>
            <span class="font-semibold text-emerald-600">A</span>
          </div>
          <div class="flex items-center justify-between">
            <span>最近一次平均分</span>
            <span class="font-semibold text-slate-900">82.5</span>
          </div>
          <div class="flex items-center justify-between">
            <span>知识点平均掌握度</span>
            <span class="font-semibold text-sky-600">78%</span>
          </div>
        </div>
      </el-card>

      <el-card class="teacher-card w-[40%] max-lg:w-full" shadow="never">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold text-slate-800">学生进度与评级</span>
            <span class="text-xs text-slate-500">双击查看详情</span>
          </div>
        </template>

        <div class="custom-scrollbar h-[280px] overflow-y-auto pr-2">
          <div
            v-for="stu in studentList"
            :key="stu.stu_id"
            class="flex cursor-pointer items-center justify-between rounded-lg border-b border-slate-100 p-3 transition-colors hover:bg-slate-50"
            @dblclick="openStudentDetail(stu)"
          >
            <span class="w-24 truncate text-sm text-slate-700">{{ stu.stu_name }}</span>
            <el-progress
              :percentage="progressPercent(stu.course_process)"
              :stroke-width="8"
              class="mx-4 flex-1"
            />
            <span class="w-8 text-center text-sm font-bold" :class="getRatingColor(stu.stu_level)">
              {{ stu.stu_level || '--' }}
            </span>
          </div>
          <div v-if="studentList.length === 0" class="py-8 text-center text-sm text-slate-400">
            当前班级暂无学生数据
          </div>
        </div>
      </el-card>

      <el-card class="teacher-card flex-1 max-lg:w-full" shadow="never">
        <template #header>
          <span class="text-sm font-bold text-slate-800">疑难章节分布图</span>
        </template>

        <div class="flex h-[280px] items-center justify-center rounded-xl bg-slate-50/80">
          <div class="flex flex-col items-center text-sm text-slate-400">
            <el-icon :size="32" class="mb-2"><PieChart /></el-icon>
            ECharts 饼图渲染区
          </div>
        </div>
      </el-card>
    </div>

    <div class="flex min-h-[360px] gap-6 max-lg:flex-col">
      <el-card class="teacher-card w-[45%] max-lg:w-full" shadow="never">
        <template #header>
          <span class="text-sm font-bold text-slate-800">AI 班级教学建议</span>
        </template>

        <div class="custom-scrollbar h-[360px] overflow-y-auto rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-sm leading-7 text-slate-700">
          结合学生评级、班级学科整体进度，以及疑难章节和知识点分布，后续可以优先围绕高频错题知识点安排专题复习。
          当前这块仍是占位内容，词云能力已经接入真实数据，后续如果需要，我们可以再把这部分联动成自动生成的教学建议。
        </div>
      </el-card>

      <el-card class="teacher-card flex-1 max-lg:w-full" shadow="never">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <span class="text-sm font-bold text-slate-800">疑难知识点词云</span>
            <span class="text-xs text-slate-500">
              {{ wordCloudList.length > 0 ? `Top ${wordCloudList.length}` : '暂无数据' }}
            </span>
          </div>
        </template>

        <div class="word-cloud-panel">
          <div
            v-if="wordCloudList.length > 0"
            ref="cloudContainerRef"
            class="word-cloud-container"
          >
            <span
              v-for="(item, idx) in wordCloudList"
              :key="item.name"
              :ref="(el) => setCloudItemRef(el, idx)"
              class="word-cloud-item"
              :class="{ 'word-cloud-item--ready': wordCloudReady }"
              :style="wordCloudStyle(item, idx)"
              :title="`${item.name} | 次数 ${item.count} | 占比 ${(item.ratio * 100).toFixed(1)}%`"
            >
              {{ item.name }}
            </span>
          </div>
          <div v-else class="flex h-full items-center justify-center text-sm text-slate-400">
            当前班级该学科暂无错题知识点数据
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="studentDialogVisible"
      title="学生详情与图谱"
      width="80%"
      class="student-detail-dialog"
      destroy-on-close
    >
      <div class="flex h-[600px] gap-6 max-lg:h-auto max-lg:flex-col">
        <div class="flex w-1/4 flex-col gap-4 max-lg:w-full">
          <el-card shadow="never" class="bg-slate-50">
            <div class="space-y-2 text-sm text-slate-700">
              <div><span class="text-slate-500">班级：</span>{{ currentClassName }}</div>
              <div><span class="text-slate-500">姓名：</span>{{ currentStudent?.stu_name || '--' }}</div>
              <div>
                <span class="text-slate-500">评级：</span>
                <span class="font-bold text-sky-600">{{ currentStudent?.stu_level || '--' }}</span>
              </div>
              <div>
                <span class="text-slate-500">进度：</span>
                {{ progressPercent(currentStudent?.course_process ?? null) }}%
              </div>
            </div>
          </el-card>

          <el-card shadow="never" class="flex-1">
            <template #header>
              <span class="text-sm font-bold">教师建议与评价</span>
            </template>

            <el-input
              v-model="teacherSuggestion"
              type="textarea"
              :rows="8"
              placeholder="可手动编辑或后续接入自动生成..."
            />
            <div class="mt-4 flex justify-end gap-2">
              <el-button size="small">生成建议</el-button>
              <el-button type="primary" size="small">保存</el-button>
            </div>
          </el-card>
        </div>

        <div class="flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-400">
          <div class="flex flex-col items-center text-sm">
            <el-icon :size="48" class="mb-2"><Share /></el-icon>
            <p>这里预留学生个人知识图谱展示区</p>
            <p class="mt-1 text-xs">后续可接入该学生的错题与掌握度图谱</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from 'vue'
import { PieChart, Share } from '@element-plus/icons-vue'
import {
  getClassStudents,
  getDifficultKnowledge,
  getTeacherClasses,
  getTeacherCourses,
  type ClassStudent,
  type DifficultKnowledgePoint,
  type TeacherClass,
  type TeacherCourse,
} from '@/api/teacher'

const selectedClass = ref<number | null>(null)
const selectedCourse = ref<number | null>(null)
const classList = ref<TeacherClass[]>([])
const courseList = ref<TeacherCourse[]>([])
const studentList = ref<ClassStudent[]>([])
const wordCloudList = ref<DifficultKnowledgePoint[]>([])
const studentDialogVisible = ref(false)
const teacherSuggestion = ref('')
const currentStudent = ref<ClassStudent | null>(null)

const cloudContainerRef = ref<HTMLElement | null>(null)
const cloudItemRefs = ref<Array<HTMLElement | null>>([])
const cloudPositions = ref<Array<{ x: number; y: number }>>([])
const wordCloudReady = ref(false)

const CLOUD_COLORS = [
  '#ef4444',
  '#f97316',
  '#f59e0b',
  '#eab308',
  '#84cc16',
  '#22c55e',
  '#10b981',
  '#14b8a6',
  '#06b6d4',
  '#0ea5e9',
  '#3b82f6',
  '#6366f1',
  '#8b5cf6',
  '#a855f7',
  '#d946ef',
  '#ec4899',
  '#f43f5e',
  '#64748b',
  '#0f766e',
  '#b45309',
]

const currentClassName = computed(() => {
  const current = classList.value.find((item) => item.class_id === selectedClass.value)
  return current?.class_name ?? '--'
})

const currentClassStudentCount = computed(() => {
  const current = classList.value.find((item) => item.class_id === selectedClass.value)
  if (!current) return '--'
  return current.student_count ?? current.classmates_num ?? '--'
})

const progressPercent = (process: number | null) => {
  if (process === null || process === undefined) return 0
  return Math.round(process * 100)
}

const loadTeacherData = async () => {
  try {
    const [courses, classes] = await Promise.all([
      getTeacherCourses(),
      getTeacherClasses(),
    ])
    courseList.value = courses
    classList.value = classes
    selectedClass.value = classes[0]?.class_id ?? null
    selectedCourse.value = courses[0]?.course_id ?? null
  } catch (error) {
    console.error('加载教师班级/学科数据失败:', error)
    classList.value = []
    courseList.value = []
  }
}

const loadStudents = async () => {
  if (selectedClass.value === null || selectedCourse.value === null) {
    studentList.value = []
    return
  }

  try {
    studentList.value = await getClassStudents(selectedClass.value, selectedCourse.value)
  } catch (error) {
    console.error('加载班级学生列表失败:', error)
    studentList.value = []
  }
}

const renderWordCloud = async () => {
  wordCloudReady.value = false
  await nextTick()
  computeCloudLayout()
}

const loadWordCloud = async () => {
  if (selectedClass.value === null || selectedCourse.value === null) {
    wordCloudList.value = []
    cloudItemRefs.value = []
    cloudPositions.value = []
    wordCloudReady.value = false
    return
  }

  try {
    cloudItemRefs.value = []
    wordCloudList.value = await getDifficultKnowledge(selectedClass.value, selectedCourse.value)
    cloudPositions.value = []
    if (wordCloudList.value.length > 0) {
      await renderWordCloud()
    } else {
      wordCloudReady.value = false
    }
  } catch (error) {
    console.error('加载疑难知识点词云失败:', error)
    wordCloudList.value = []
    cloudItemRefs.value = []
    cloudPositions.value = []
    wordCloudReady.value = false
  }
}

const loadDashboardData = async () => {
  await Promise.all([loadStudents(), loadWordCloud()])
}

const setCloudItemRef = (
  el: Element | ComponentPublicInstance | null,
  idx: number,
) => {
  cloudItemRefs.value[idx] = el as HTMLElement | null
}

const cloudFontSize = (item: DifficultKnowledgePoint) => {
  const maxRatio = wordCloudList.value[0]?.ratio || 1
  return 14 + (item.ratio / maxRatio) * 18
}

const computeCloudLayout = () => {
  const container = cloudContainerRef.value
  const items = wordCloudList.value
  if (!container || items.length === 0) {
    wordCloudReady.value = false
    return
  }

  const width = container.clientWidth
  const height = container.clientHeight
  const halfWidth = Math.max(width / 2 - 18, 0)
  const halfHeight = Math.max(height / 2 - 18, 0)
  const maxRadius = Math.hypot(halfWidth, halfHeight)

  const boxes = items.map((item, idx) => {
    const el = cloudItemRefs.value[idx]
    return {
      width: el?.offsetWidth ?? item.name.length * cloudFontSize(item),
      height: el?.offsetHeight ?? cloudFontSize(item) * 1.5,
    }
  })

  const placed: Array<{ cx: number; cy: number; hw: number; hh: number }> = []
  const positions: Array<{ x: number; y: number }> = []

  const overlaps = (cx: number, cy: number, hw: number, hh: number) => {
    const gap = 8
    return placed.some((item) => {
      return (
        Math.abs(cx - item.cx) < hw + item.hw + gap &&
        Math.abs(cy - item.cy) < hh + item.hh + gap
      )
    })
  }

  const outOfBounds = (cx: number, cy: number, hw: number, hh: number) => {
    return Math.abs(cx) + hw > halfWidth || Math.abs(cy) + hh > halfHeight
  }

  boxes.forEach((box, idx) => {
    const hw = box.width / 2
    const hh = box.height / 2

    if (idx === 0) {
      placed.push({ cx: 0, cy: 0, hw, hh })
      positions.push({ x: 0, y: 0 })
      return
    }

    let candidateX = 0
    let candidateY = 0
    let found = false

    for (let step = 1; step <= 2400; step += 1) {
      const angle = step * 2.399963229728653
      const radius = Math.min(maxRadius, 6 + step * 2.2)
      const tx = Math.cos(angle) * radius
      const ty = Math.sin(angle) * radius

      if (outOfBounds(tx, ty, hw, hh)) {
        continue
      }

      candidateX = tx
      candidateY = ty

      if (!overlaps(tx, ty, hw, hh)) {
        found = true
        break
      }
    }

    placed.push({ cx: candidateX, cy: candidateY, hw, hh })
    positions.push({
      x: candidateX,
      y: candidateY,
    })

    if (!found) {
      console.warn(`词云项 "${items[idx]?.name}" 未找到完全无碰撞位置，已使用兜底位置`)
    }
  })

  cloudPositions.value = positions
  wordCloudReady.value = true
}

const wordCloudStyle = (item: DifficultKnowledgePoint, idx: number) => {
  const position = cloudPositions.value[idx] ?? { x: 0, y: 0 }
  return {
    fontSize: `${cloudFontSize(item)}px`,
    color: CLOUD_COLORS[idx % CLOUD_COLORS.length],
    '--cloud-x': `${position.x}px`,
    '--cloud-y': `${position.y}px`,
    zIndex: Math.max(1, 30 - idx),
  } as Record<string, string | number>
}

const openStudentDetail = (student: ClassStudent) => {
  currentStudent.value = student
  teacherSuggestion.value = ''
  studentDialogVisible.value = true
}

const getRatingColor = (level: string | null) => {
  if (level === 'A') return 'text-emerald-600'
  if (level === 'B') return 'text-sky-600'
  if (level === 'C') return 'text-amber-500'
  return 'text-slate-500'
}

const handleResize = () => {
  if (wordCloudList.value.length === 0) return
  window.requestAnimationFrame(() => {
    computeCloudLayout()
  })
}

watch([selectedClass, selectedCourse], () => {
  void loadDashboardData()
})

onMounted(() => {
  void loadTeacherData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.teacher-card {
  border-radius: 18px;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.04);
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.16);
  border-radius: 999px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(15, 23, 42, 0.26);
}

.word-cloud-panel {
  height: 360px;
  overflow: hidden;
  border-radius: 18px;
  background:
    radial-gradient(circle at top, rgba(14, 165, 233, 0.12), transparent 42%),
    radial-gradient(circle at bottom, rgba(249, 115, 22, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(241, 245, 249, 0.9));
}

.word-cloud-container {
  position: relative;
  height: 100%;
  width: 100%;
}

.word-cloud-item {
  position: absolute;
  left: 50%;
  top: 50%;
  white-space: nowrap;
  font-weight: 700;
  line-height: 1.1;
  user-select: none;
  opacity: 0;
  text-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  transform: translate(-50%, -50%) translate(var(--cloud-x), var(--cloud-y));
  transition:
    transform 0.2s ease,
    opacity 0.2s ease,
    filter 0.2s ease;
}

.word-cloud-item--ready {
  opacity: 0.96;
}

.word-cloud-item:hover {
  filter: brightness(1.05);
  transform: translate(-50%, -50%) translate(var(--cloud-x), var(--cloud-y)) scale(1.08);
}

:deep(.student-detail-dialog) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.student-detail-dialog .el-dialog__body) {
  background: #f8fafc;
  padding: 20px;
}
</style>
