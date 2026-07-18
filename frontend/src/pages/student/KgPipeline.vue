<template>
  <div class="kgp-page">
    <h1 class="page-title">知识图谱自动构建</h1>

    <el-card class="upload-card">
      <template #header><span>上传文档</span></template>
      <el-upload
        v-model:file-list="fileList"
        action="#"
        :auto-upload="false"
        :before-upload="beforeUpload"
        :limit="5"
        multiple
        drag
        accept=".pdf,.md,.txt"
        class="upload-area"
      >
        <el-icon class="upload-icon"><upload-filled /></el-icon>
        <div class="upload-text">拖拽文件到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 PDF、Markdown、TXT 格式，单文件最大 50MB，单次最多 5 个文件
          </div>
        </template>
      </el-upload>
    </el-card>

    <div class="submit-area">
      <StarBorder as="div" color="#409eff" speed="3s">
        <el-button type="primary" size="large" :loading="isSubmitting" :disabled="fileList.length === 0" @click="handleSubmit">
          开始构建知识图谱
        </el-button>
      </StarBorder>
    </div>

    <el-card v-if="tasks.length > 0" class="tasks-card">
      <template #header><span>任务列表</span></template>
      <div class="task-list">
        <div v-for="task in tasks" :key="task.taskId" class="task-item" :class="`task-${task.status}`">
          <div class="task-header">
            <span class="task-file">{{ task.fileName }}</span>
            <el-tag :type="statusType(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag>
          </div>

          <div v-if="task.status === 'pending' || task.status === 'processing'" class="task-progress">
            <el-progress :percentage="taskProgress(task)" :status="task.status === 'processing' ? '' : 'warning'" :indeterminate="task.status === 'processing'" />
            <span class="task-phase">{{ phaseLabel(task.status) }}</span>
            <span class="task-time">已耗时: {{ elapsed(task) }}</span>
          </div>

          <div v-else-if="task.status === 'completed'" class="task-result">
            <div class="result-stats">
              <div class="result-item"><span class="label">节点</span><span class="value">{{ task.nodes ?? '-' }}</span></div>
              <div class="result-item"><span class="label">边</span><span class="value">{{ task.edges ?? '-' }}</span></div>
              <div class="result-item"><span class="label">切片</span><span class="value">{{ task.chunks ?? '-' }}</span></div>
            </div>
            <StarBorder as="div" color="#67c23a" speed="4s">
              <el-button type="success" @click="goToGraph">查看知识图谱</el-button>
            </StarBorder>
          </div>

          <div v-else-if="task.status === 'failed'" class="task-error">
            <el-alert :title="task.error || '构建失败'" type="error" :closable="false" show-icon />
          </div>

          <StarBorder as="div" color="#f56c6c" speed="5s">
            <el-button type="danger" size="small" text @click="removeTask(task.taskId)">移除</el-button>
          </StarBorder>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { useKgPipeline, type KgTask } from '@/composables/useKgPipeline'
import StarBorder from '@/components/StarBorder.vue'

const router = useRouter()
const { tasks, isSubmitting, submitTask, removeTask } = useKgPipeline()
const fileList = ref<UploadFile[]>([])

const ALLOWED_EXTS = ['.pdf', '.md', '.txt', '.markdown']

function beforeUpload(file: File): boolean {
  const ext = file.name.toLowerCase().split('.').pop()
  if (!ext || !ALLOWED_EXTS.some(e => e.endsWith(ext!))) {
    ElMessage.error('仅支持 PDF、Markdown、TXT 格式')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('单文件大小不能超过 50MB')
    return false
  }
  return true
}

async function handleSubmit(): Promise<void> {
  const files = fileList.value.filter(f => f.raw).map(f => f.raw as File)
  if (!files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  for (const file of files) {
    try {
      await submitTask(file)
    } catch (e: any) {
      ElMessage.error(e?.message || '提交失败')
    }
  }
  fileList.value = []
  ElMessage.success('任务已提交')
}

function goToGraph(): void {
  router.push('/student/knowledge')
}

function statusType(s: string): string {
  return { pending: 'warning', processing: '', completed: 'success', failed: 'danger' }[s] || 'info'
}

function statusLabel(s: string): string {
  return { pending: '等待中', processing: '处理中', completed: '已完成', failed: '失败' }[s] || s
}

function phaseLabel(s: string): string {
  if (s === 'pending') return '任务已提交，等待处理...'
  if (s === 'processing') return '正在解析文档并提取知识图谱...'
  return ''
}

function taskProgress(task: KgTask): number {
  if (task.status === 'pending') return 5
  if (task.status === 'processing') return 60
  if (task.status === 'completed') return 100
  return 0
}

function elapsed(task: KgTask): string {
  const d = (Date.now() - new Date(task.createdAt).getTime()) / 1000
  if (d < 60) return `${Math.floor(d)}秒`
  if (d < 3600) return `${Math.floor(d / 60)}分${Math.floor(d % 60)}秒`
  return `${Math.floor(d / 3600)}时${Math.floor((d % 3600) / 60)}分`
}
</script>

<style scoped>
.kgp-page { padding: 20px; max-width: 800px; margin: 0 auto; }
.page-title { font-size: 24px; margin-bottom: 20px; text-align: center; }
.upload-card, .tasks-card { margin-bottom: 20px; }
.upload-area { width: 100%; }
.upload-icon { font-size: 48px; color: #909399; margin-bottom: 10px; }
.upload-text { color: #606266; }
.upload-text em { color: #409eff; font-style: normal; }
.upload-tip { font-size: 12px; color: #909399; margin-top: 10px; }
.submit-area { text-align: center; margin-bottom: 20px; }
.task-list { display: flex; flex-direction: column; gap: 12px; }
.task-item { border: 1px solid #ebeef5; border-radius: 4px; padding: 12px; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.task-file { font-weight: bold; color: #303133; word-break: break-all; }
.task-progress { margin-top: 8px; }
.task-phase { display: block; font-size: 12px; color: #909399; margin: 4px 0; }
.task-time { font-size: 12px; color: #909399; }
.task-result { margin-top: 10px; }
.result-stats { display: flex; gap: 16px; margin-bottom: 12px; }
.result-item { display: flex; flex-direction: column; align-items: center; padding: 8px 16px; background: #f5f7fa; border-radius: 4px; }
.result-item .label { font-size: 12px; color: #909399; }
.result-item .value { font-size: 20px; font-weight: bold; color: #303133; }
.task-error { margin-top: 10px; }
</style>
