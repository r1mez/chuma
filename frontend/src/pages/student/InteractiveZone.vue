<template>
  <BorderGlow class="interactive-page" background-color="transparent">
    <div class="glass-card page-container">
      <h2 class="page-title">互动专区</h2>
      
      <!-- 列表区域，独立滚动 -->
      <div class="list-container scroll-area">
        <el-table
          :data="pagedData"
          style="width: 100%; background: transparent;"
          row-class-name="interactive-row"
          header-row-class-name="interactive-header"
          @row-dblclick="handleRowDblclick"
        >
          <el-table-column prop="studentName" label="学生" width="120" />
          <el-table-column prop="content" label="问题、对话、描述等" min-width="300">
            <template #default="scope">
              <span class="text-truncate">{{ scope.row.content }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="replyCount" label="回答数" width="120">
            <template #default="scope">
              回答数×{{ scope.row.replyCount }}
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="150" align="right" />
        </el-table>
      </div>

      <!-- 分页区域 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          class="custom-pagination"
        />
      </div>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import BorderGlow from '@/components/BorderGlow.vue'

const router = useRouter()

// 模拟数据
const mockData = Array.from({ length: 45 }).map((_, index) => {
  const isA = index % 2 === 0
  return {
    id: index + 1,
    studentName: isA ? '学生A' : '学生B',
    content: `问题、对话、描述等占位 占位 占位 ${index + 1}...`,
    replyCount: index % 4,
    time: '2026-07-20 10:00'
  }
})

const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(mockData.length)

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return mockData.slice(start, start + pageSize.value)
})

const handleRowDblclick = (row: any) => {
  router.push(`/student/interactive/${row.id}`)
}
</script>

<style scoped>
.interactive-page {
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
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  font-weight: bold;
  color: #000;
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

/* 覆盖 el-table 的默认背景使其透明以适配玻璃态 */
:deep(.el-table) {
  background-color: transparent !important;
  --el-table-border-color: rgba(0, 0, 0, 0.1);
  --el-table-header-bg-color: rgba(255, 255, 255, 0.3);
  --el-table-tr-bg-color: transparent;
  color: #000;
}

:deep(.el-table th.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.4) !important;
  color: #000;
  font-weight: bold;
}

:deep(.el-table tr) {
  background-color: transparent !important;
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.el-table tr:hover > td.el-table__cell) {
  background-color: rgba(255, 255, 255, 0.5) !important;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

/* 分页组件样式覆盖 */
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