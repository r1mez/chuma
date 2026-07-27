<template>
  <BorderGlow class="exercise-records-page" background-color="transparent">
    <div class="records-layout">
      <!-- 左侧：学科卡片 -->
      <div class="left-panel">
        <div class="grid-container">
          <div 
            v-for="subject in subjects" 
            :key="subject.id" 
            class="glass-card subject-card"
            @click="enterSubjectDetail(subject.id)"
          >
            <span class="subject-name">{{ subject.name }}做题记录</span>
          </div>
        </div>
      </div>

      <!-- 右侧：错题记录列表 -->
      <div class="right-panel glass-card">
        <div class="right-header">
          <h3 class="panel-title">错题记录</h3>
          <div class="search-box">
            <el-input
              v-model="searchQuery"
              placeholder="搜索错题..."
              clearable
            >
              <template #append>
                <el-button @click="handleSearch">搜索</el-button>
              </template>
            </el-input>
          </div>
        </div>
        <div class="records-list scroll-area">
          <div 
            v-for="record in pagedWrongRecords" 
            :key="record.id" 
            class="record-item"
            @dblclick="goToPracticePanel(record.id)"
          >
            <div class="record-stem text-truncate" :title="record.stem">
              {{ record.stem }}
            </div>
            <div class="record-meta">
              <div class="tags">
                <span v-for="(tag, idx) in record.tags" :key="idx" class="tag">
                  {{ tag }}
                </span>
              </div>
              <div class="date">{{ record.date }}</div>
            </div>
          </div>
        </div>
        
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="wrongRecords.length"
            layout="total, prev, pager, next"
            class="custom-pagination"
          />
        </div>
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BorderGlow from '@/components/BorderGlow.vue'

const router = useRouter()

const searchQuery = ref('')
const handleSearch = () => {
  ElMessage.success(`搜索错题：${searchQuery.value}`)
}

// 跳转到具体学科做题记录
const enterSubjectDetail = (subjectId: string) => {
  router.push({
    path: '/student/subject-records',
    query: { module: subjectId }
  })
}

// 双击跳转到错题练习面板
const goToPracticePanel = (questionId: number) => {
  router.push({
    path: '/student/practice/panel',
    query: { questionId: questionId }
  })
}

// 学科数据
const subjects = [
  { id: 'ds', name: '数据结构' },
  { id: 'co', name: '计算机组成原理' },
  { id: 'os', name: '操作系统' },
  { id: 'net', name: '计算机网络' }
]

// 模拟所有学科的错题集合
const wrongRecords = Array.from({ length: 45 }).map((_, index) => {
  return {
    id: 1000 + index,
    stem: `题目... 占位错题内容 ${index + 1}`,
    tags: ['知识点1', '知识点2'],
    date: '时间'
  }
})

// 分页逻辑
const currentPage = ref(1)
const pageSize = ref(10)

const pagedWrongRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return wrongRecords.slice(start, start + pageSize.value)
})
</script>

<style scoped>
.exercise-records-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.records-layout {
  display: flex;
  gap: 24px;
  height: 100%;
  padding: 24px;
}

/* 玻璃拟态卡片基础样式 */
.glass-card {
  background: #e5e8e4;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* --- 左侧面板：四宫格 --- */
.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 24px;
}

.subject-card {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.6);
}

.subject-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.9);
}

.subject-name {
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
}

/* --- 右侧面板：错题记录 --- */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
}

.right-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
  position: relative;
}

.panel-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: bold;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.search-box {
  width: 200px;
  margin-left: auto; /* push to right if absolute center doesn't push it */
}
:deep(.search-box .el-input__wrapper) {
  background: transparent;
  box-shadow: 0 0 0 1px #666 inset;
}
:deep(.search-box .el-input-group__append) {
  background: transparent;
  border: 1px solid #666;
  border-left: none;
  color: #333;
}

.records-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 滚动区域通用样式 */
.scroll-area {
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

/* 记录项 */
.record-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.record-item:hover {
  background: rgba(255, 255, 255, 0.8);
}

.record-stem {
  flex: 1;
  margin-right: 16px;
  font-size: 0.95rem;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 0.85rem;
  color: #666;
}

.date {
  font-size: 0.85rem;
  color: #666;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

:deep(.custom-pagination .el-pager li) {
  background: transparent;
  color: #000;
}
:deep(.custom-pagination .el-pager li.is-active) {
  font-weight: bold;
  color: #2980b9;
}
:deep(.custom-pagination button) {
  background: transparent !important;
  color: #000;
}
</style>