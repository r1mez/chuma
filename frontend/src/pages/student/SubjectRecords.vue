<template>
  <BorderGlow class="subject-records-page" background-color="transparent">
    <div class="glass-card page-container">
      <h2 class="page-title">{{ subjectName }}做题记录</h2>
      
      <!-- 记录列表区域，独立滚动 -->
      <div class="list-container scroll-area">
        <div class="records-list">
          <div 
            v-for="record in pagedRecords" 
            :key="record.id" 
            class="record-item"
            :class="record.isCorrect ? 'correct-item' : 'incorrect-item'"
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
        <div class="spacer"></div>
      </div>

      <!-- 分页区域 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalRecords"
          layout="total, prev, pager, next"
          class="custom-pagination"
        />
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BorderGlow from '@/components/BorderGlow.vue'

const route = useRoute()
const router = useRouter()

const moduleId = route.query.module as string

// 根据 moduleId 获取学科名称
const subjectMap: Record<string, string> = {
  'ds': '数据结构',
  'co': '计算机组成原理',
  'os': '操作系统',
  'net': '计算机网络'
}
const subjectName = computed(() => subjectMap[moduleId] || '学科')

// 模拟学科的做题记录（包含对错状态）
const mockRecords = Array.from({ length: 45 }).map((_, index) => {
  return {
    id: 2000 + index,
    stem: `题目... 这是一道${subjectName.value}的占位题目记录 ${index + 1}`,
    tags: ['知识点1', '知识点2'],
    date: '2026-07-20 10:00',
    isCorrect: index % 3 !== 0 // 模拟对错，部分错误，部分正确
  }
})

const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = ref(mockRecords.length)

const pagedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return mockRecords.slice(start, start + pageSize.value)
})

// 双击跳转到错题练习面板
const goToPracticePanel = (questionId: number) => {
  router.push({
    path: '/student/practice/panel',
    query: { questionId: questionId }
  })
}
</script>

<style scoped>
.subject-records-page {
  color: #000;
  height: calc(100vh - 170px);
  margin: 20px;
}

.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #e5e8e4;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.page-title {
  margin: 0 0 24px 0;
  font-size: 1.5rem;
  font-weight: bold;
  color: #000;
  text-align: center;
  flex-shrink: 0;
}

.list-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scroll-area {
  overflow-y: auto;
  padding: 0 40px; /* 列表左右留白，符合线框图居中感 */
}

/* 自定义滚动条 */
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

.records-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* --- 记录项样式及对错状态区分 --- */
.record-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.record-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* 正确的记录：绿色框包围与微绿背景 */
.correct-item {
  background-color: rgba(39, 174, 96, 0.1);
  border-color: rgba(39, 174, 96, 0.3);
}
.correct-item:hover {
  background-color: rgba(39, 174, 96, 0.2);
  border-color: rgba(39, 174, 96, 0.5);
}

/* 错误的记录：红色框包围与微红背景 */
.incorrect-item {
  background-color: rgba(231, 76, 60, 0.1);
  border-color: rgba(231, 76, 60, 0.3);
}
.incorrect-item:hover {
  background-color: rgba(231, 76, 60, 0.2);
  border-color: rgba(231, 76, 60, 0.5);
}

.record-stem {
  flex: 1;
  font-size: 1rem;
  color: #333;
  margin-right: 24px;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-shrink: 0;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  font-size: 0.9rem;
  color: #666;
}

.date {
  font-size: 0.9rem;
  color: #666;
  width: 140px;
  text-align: right;
}

.spacer {
  height: 20px;
}

/* 分页组件样式覆盖 */
.pagination-container {
  margin-top: 20px;
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