<template>
  <div class="assignments-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">LEARNING TASKS</p>
        <h2>我的作业</h2>
        <p>查看教师布置的作业，作答结果会同步到做题记录和知识点掌握度。</p>
      </div>
      <el-button :loading="loading" @click="loadAssignments">刷新</el-button>
    </section>

    <div v-loading="loading" class="assignment-grid">
      <el-card v-for="assignment in assignments" :key="assignment.assignment_id" shadow="never" class="assignment-card">
        <div class="assignment-card-top">
          <el-tag size="small" type="success" effect="plain">{{ assignment.course_name || '课程作业' }}</el-tag>
          <span class="due-date" :class="{ overdue: isOverdue(assignment.due_at) }">{{ dueText(assignment.due_at) }}</span>
        </div>
        <h3>{{ assignment.title }}</h3>
        <p class="description">{{ assignment.description || '教师未填写作业说明' }}</p>
        <div class="assignment-meta">
          <span>{{ assignment.class_name || '当前班级' }}</span>
          <span>{{ assignment.submitted_count }}/{{ assignment.question_count }} 题已提交</span>
        </div>
        <el-progress :percentage="progress(assignment)" :show-text="false" :stroke-width="7" />
        <el-button type="primary" plain class="start-button" @click="startAssignment(assignment)">
          {{ assignment.submitted_count ? '继续作答' : '开始作答' }}
        </el-button>
      </el-card>
    </div>
    <el-empty v-if="!loading && assignments.length === 0" description="暂无教师作业" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchStudentAssignments, type StudentAssignment } from '@/api/assignments'

const router = useRouter()
const assignments = ref<StudentAssignment[]>([])
const loading = ref(false)

const progress = (assignment: StudentAssignment) => assignment.question_count
  ? Math.round(assignment.submitted_count / assignment.question_count * 100)
  : 0

const isOverdue = (value?: string | null) => Boolean(value && new Date(value).getTime() < Date.now())
const dueText = (value?: string | null) => value ? (isOverdue(value) ? `已截止 ${new Date(value).toLocaleString('zh-CN', { hour12: false })}` : `截止 ${new Date(value).toLocaleString('zh-CN', { hour12: false })}`) : '无截止时间'

const loadAssignments = async () => {
  loading.value = true
  try {
    assignments.value = await fetchStudentAssignments()
  } catch {
    ElMessage.error('作业加载失败')
  } finally {
    loading.value = false
  }
}

const startAssignment = (assignment: StudentAssignment) => {
  if (isOverdue(assignment.due_at)) {
    ElMessage.warning('该作业已截止')
    return
  }
  router.push({ path: '/student/practice/panel', query: { assignmentId: String(assignment.assignment_id) } })
}

onMounted(loadAssignments)
</script>

<style scoped>
.assignments-page { display: flex; flex-direction: column; gap: 22px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.page-heading h2 { margin: 3px 0 6px; color: #17243c; font-size: 25px; }
.page-heading p:not(.eyebrow) { margin: 0; color: #718096; font-size: 13px; }
.eyebrow { margin: 0; color: #2d5ac0; font-size: 11px; font-weight: 700; letter-spacing: .12em; }
.assignment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }
.assignment-card { border-color: #e2e8f0; border-radius: 14px; }
.assignment-card-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.due-date { color: #667085; font-size: 12px; }
.due-date.overdue { color: #d92d20; }
.assignment-card h3 { margin: 16px 0 8px; color: #27364f; font-size: 18px; }
.description { min-height: 38px; margin: 0 0 18px; color: #7a8699; font-size: 13px; line-height: 1.6; }
.assignment-meta { display: flex; justify-content: space-between; margin-bottom: 10px; color: #667085; font-size: 12px; }
.start-button { width: 100%; margin-top: 18px; }
@media (max-width: 640px) { .page-heading { flex-direction: column; } }
</style>
