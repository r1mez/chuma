<template>
  <div class="teacher-page h-full flex flex-col gap-6 p-4">
    <!-- 顶部班级选择与概览 -->
    <div class="flex gap-6 h-[40%] min-h-[300px]">
      <!-- 班级信息面板 (左侧) -->
      <el-card class="w-1/4 flex flex-col" shadow="never">
        <template #header>
          <div class="flex gap-3">
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
        <div class="space-y-4 text-sm text-gray-700">
          <div class="flex justify-between"><span>学生数量:</span> <span class="font-bold">{{ currentClassStudentCount }}</span></div>
          <div class="flex justify-between"><span>整体班级AI评级:</span> <span class="font-bold text-green-600">A</span></div>
          <div class="flex justify-between"><span>最近作业/考试平均分:</span> <span class="font-bold">82.5</span></div>
          <div class="flex justify-between"><span>知识点平均掌握度:</span> <span class="font-bold text-blue-600">78%</span></div>
        </div>
      </el-card>

      <!-- 学习进度条 (学生列表) - 移至顶部中间 -->
      <el-card class="w-[40%] flex flex-col" shadow="never">
        <template #header>
          <div class="flex justify-between items-center">
            <span class="font-bold text-gray-800 text-sm">学生进度与评级</span>
            <span class="text-xs text-gray-500">双击查看详情</span>
          </div>
        </template>
        <div class="overflow-y-auto h-full pr-2 custom-scrollbar">
          <div 
            v-for="stu in studentList" :key="stu.stu_id" 
            class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors border-b border-gray-50 last:border-0"
            @dblclick="openStudentDetail(stu)"
          >
            <span class="w-24 text-sm text-gray-700 truncate">{{ stu.stu_name }}</span>
            <el-progress :percentage="progressPercent(stu.course_process)" :stroke-width="8" class="flex-1 mx-4" />
            <span class="w-8 text-center font-bold text-sm" :class="getRatingColor(stu.stu_level)">
              {{ stu.stu_level || '—' }}
            </span>
          </div>
          <div v-if="studentList.length === 0" class="py-8 text-center text-gray-400 text-sm">
            该班级暂无学生数据
          </div>
        </div>
      </el-card>

      <!-- 疑难章节分布图 (饼图) - 右侧 -->
      <el-card class="flex-1" shadow="never">
        <template #header>
          <span class="font-bold text-gray-800 text-sm">疑难章节分布图</span>
        </template>
        <div class="h-full w-full flex items-center justify-center bg-gray-50/50 rounded-lg">
          <!-- 饼图占位 -->
          <div class="text-gray-400 text-sm flex flex-col items-center">
            <el-icon :size="32" class="mb-2"><PieChart /></el-icon>
            ECharts 饼图渲染区
          </div>
        </div>
      </el-card>
    </div>

    <!-- 底部详情展示区 -->
    <div class="flex gap-6 h-[60%] min-h-[350px]">
      <!-- AI 班级教学建议 - 移至左下角独立卡片 -->
      <el-card class="w-[45%] flex flex-col" shadow="never">
        <template #header>
          <span class="font-bold text-gray-800 text-sm">AI 班级教学建议</span>
        </template>
        <div class="h-full border border-gray-200 rounded-lg bg-gray-50/50 p-4">
          <p class="text-sm text-gray-700 leading-relaxed overflow-y-auto h-full custom-scrollbar">
            结合所有学生评级、班级学科教学进度、疑难章节与知识点，教师端 agent 总结下一步教学建议：<br><br>
            建议下一步重点复习"图的遍历算法"与"B树"，多数学生在最近作业中表现出对图的深度优先搜索理解不深。可以通过增加互动专区的相关练习题来巩固。
          </p>
        </div>
      </el-card>

      <!-- 疑难知识点词云 - 右下角 -->
      <el-card class="flex-1" shadow="never">
        <template #header>
          <span class="font-bold text-gray-800 text-sm">疑难知识点词云</span>
        </template>
        <div class="h-full w-full flex items-center justify-center bg-gray-50/50 rounded-lg">
          <!-- 词云占位 -->
          <div class="text-gray-400 text-sm flex flex-col items-center">
            <el-icon :size="32" class="mb-2"><DataAnalysis /></el-icon>
            ECharts 词云渲染区
          </div>
        </div>
      </el-card>
    </div>

    <!-- 学生详细图谱弹窗 -->
    <el-dialog
      v-model="studentDialogVisible"
      title="学生详情与图谱"
      width="80%"
      class="student-detail-dialog"
      destroy-on-close
    >
      <div class="flex gap-6 h-[600px]">
        <!-- 左侧面板 -->
        <div class="w-1/4 flex flex-col gap-4">
          <el-card shadow="never" class="bg-gray-50">
            <div class="space-y-2 text-sm">
              <div><span class="text-gray-500">班级:</span> {{ currentClassName }}</div>
              <div><span class="text-gray-500">姓名:</span> {{ currentStudent?.stu_name || '—' }}</div>
              <div><span class="text-gray-500">评级:</span> <span class="font-bold text-blue-600">{{ currentStudent?.stu_level || '—' }}</span></div>
              <div><span class="text-gray-500">进度:</span> {{ progressPercent(currentStudent?.course_process ?? null) }}%</div>
            </div>
          </el-card>
          <el-card shadow="never" class="flex-1 flex flex-col">
            <template #header><span class="text-sm font-bold">教师建议与评估</span></template>
            <el-input
              v-model="teacherSuggestion"
              type="textarea"
              :rows="8"
              placeholder="可手动编辑或由Agent生成..."
              class="flex-1"
            />
            <div class="mt-4 flex justify-end">
              <el-button size="small">Agent生成</el-button>
              <el-button type="primary" size="small">保存</el-button>
            </div>
          </el-card>
        </div>
        
        <!-- 右侧图谱面板 -->
        <div class="flex-1 border border-gray-200 rounded-lg relative overflow-hidden bg-gray-50 flex items-center justify-center">
           <div class="text-gray-400 text-sm flex flex-col items-center">
            <el-icon :size="48" class="mb-2"><Share /></el-icon>
            <p>基于该学生做题正确率/错题生成的 3D 知识图谱</p>
            <p class="text-xs mt-1">支持点击节点编辑、双击连线删除</p>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { PieChart, DataAnalysis, Share } from '@element-plus/icons-vue'
import { getTeacherCourses, getTeacherClasses, getClassStudents, type TeacherCourse, type TeacherClass, type ClassStudent } from '@/api/teacher'

const selectedClass = ref<number | null>(null)
const selectedCourse = ref<number | null>(null)
const classList = ref<TeacherClass[]>([])
const courseList = ref<TeacherCourse[]>([])
const studentList = ref<ClassStudent[]>([])
const studentDialogVisible = ref(false)
const teacherSuggestion = ref('')
const currentStudent = ref<ClassStudent | null>(null)

// 当前选中班级名称
const currentClassName = computed(() => {
  const cls = classList.value.find((c) => c.class_id === selectedClass.value)
  return cls?.class_name ?? '—'
})

// 当前选中班级的学生数量（优先取数据库统计值，其次取班级表字段）
const currentClassStudentCount = computed(() => {
  const cls = classList.value.find((c) => c.class_id === selectedClass.value)
  if (!cls) return '—'
  return cls.student_count ?? cls.classmates_num ?? '—'
})

// 学科进度：course_process 为 0~1 的小数，0.5 即 50%
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
    if (classes.length > 0) selectedClass.value = classes[0].class_id
    if (courses.length > 0) selectedCourse.value = courses[0].course_id
  } catch (e) {
    console.error('加载教师学科/班级数据失败:', e)
  }
}

// 根据选中的班级与学科加载学生列表（含进度与评级）
const loadStudents = async () => {
  if (selectedClass.value === null || selectedCourse.value === null) {
    studentList.value = []
    return
  }
  try {
    studentList.value = await getClassStudents(selectedClass.value, selectedCourse.value)
  } catch (e) {
    console.error('加载班级学生列表失败:', e)
    studentList.value = []
  }
}

// 班级或学科切换时重新加载学生列表
watch([selectedClass, selectedCourse], loadStudents)

onMounted(loadTeacherData)

const openStudentDetail = (stu: ClassStudent) => {
  currentStudent.value = stu
  studentDialogVisible.value = true
  teacherSuggestion.value = ''
}

const getRatingColor = (level: string | null) => {
  if (level === 'A') return 'text-green-600'
  if (level === 'B') return 'text-blue-600'
  if (level === 'C') return 'text-orange-500'
  return 'text-gray-500'
}
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

:deep(.student-detail-dialog) {
  border-radius: 12px;
  overflow: hidden;
}
:deep(.student-detail-dialog .el-dialog__body) {
  padding: 20px;
  background: #f8fafc;
}
</style>
