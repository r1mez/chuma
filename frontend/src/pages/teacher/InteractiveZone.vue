<template>
  <div class="teacher-page h-full flex flex-col gap-6 p-4">
    <!-- 上半部分：互动列表 -->
    <el-card class="h-1/2 flex flex-col" shadow="never">
      <template #header>
        <span class="font-bold text-gray-800 text-sm">互动专区 (答疑列表)</span>
        <span class="text-xs text-gray-500 ml-4">双击跳转详细对话面板</span>
      </template>
      <div class="h-full flex flex-col">
        <el-table
          :data="pagedData"
          style="width: 100%; background: transparent;"
          class="flex-1"
          @row-dblclick="handleRowDblclick"
        >
          <el-table-column prop="studentName" label="学生" width="120" />
          <el-table-column prop="content" label="问题、对话、描述等" min-width="300">
            <template #default="scope">
              <span class="truncate">{{ scope.row.content }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="replyCount" label="回答数" width="120">
            <template #default="scope">
              回答数 × {{ scope.row.replyCount }}
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="150" align="right" />
        </el-table>
        <div class="mt-4 flex justify-center">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
          />
        </div>
      </div>
    </el-card>

    <!-- 下半部分：作业/考试推送 -->
    <el-card class="h-1/2 flex flex-col" shadow="never">
      <template #header>
        <span class="font-bold text-gray-800 text-sm">作业 / 考试推送</span>
      </template>
      <div class="h-full flex gap-6">
        <!-- 操作区 -->
        <div class="w-48 flex flex-col gap-4">
          <div class="text-sm text-gray-600 mb-2">配置生成条件：</div>
          <el-select v-model="targetClass" placeholder="选择推送班级" size="small">
            <el-option label="2026级 计科1班" value="class1" />
            <el-option label="2026级 软件2班" value="class2" />
          </el-select>
          <el-select v-model="targetChapter" placeholder="选择章节范围" size="small">
            <el-option label="数据结构 - 图" value="ch1" />
            <el-option label="计算机组成 - CPU" value="ch2" />
          </el-select>
          <el-button type="primary" @click="generateContent" :loading="isGenerating" class="mt-auto">
            点击生成
          </el-button>
        </div>
        <!-- 内容展示区 -->
        <div class="flex-1 border border-gray-200 rounded-lg bg-gray-50/50 p-4 overflow-y-auto custom-scrollbar relative">
          <div v-if="!generatedContent" class="h-full flex items-center justify-center text-gray-400 text-sm">
            Agent 生成作业 / 考试内容展示区
          </div>
          <div v-else class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {{ generatedContent }}
          </div>
        </div>
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="详细对话面板"
      width="70%"
      destroy-on-close
    >
      <div class="flex flex-col h-[500px] border border-gray-200 rounded-lg">
        <!-- 问题区 -->
        <div class="p-4 border-b border-gray-200 bg-gray-50 min-h-[100px]">
          <div class="font-bold text-sm text-gray-800 mb-2">问题区:</div>
          <div class="text-sm text-gray-700">
            <span class="font-bold mr-2">{{ currentDetail?.studentName }}:</span>
            {{ currentDetail?.content }}
          </div>
        </div>
        <!-- 答疑区 -->
        <div class="flex-1 p-4 overflow-y-auto custom-scrollbar bg-white">
          <div class="font-bold text-sm text-gray-800 mb-4">答疑区:</div>
          
          <div class="mb-4">
            <div class="text-xs text-gray-500 mb-1">老师:</div>
            <div class="bg-blue-50 p-3 rounded-lg text-sm text-gray-700 inline-block max-w-[80%]">
              这个问题考察的是关于二叉树的遍历，你需要注意...
            </div>
          </div>

          <div class="mb-4 text-right">
            <div class="text-xs text-gray-500 mb-1">{{ currentDetail?.studentName }}:</div>
            <div class="bg-gray-100 p-3 rounded-lg text-sm text-gray-700 inline-block max-w-[80%] text-left">
              老师，那如果改成后序遍历呢？
            </div>
          </div>
          
          <div class="mb-4">
            <div class="text-xs text-gray-500 mb-1">老师:</div>
            <div class="bg-blue-50 p-3 rounded-lg text-sm text-gray-700 inline-block max-w-[80%]">
              后序遍历的话，顺序就变成了左右根。
            </div>
          </div>
        </div>
        <!-- 底部回复输入 -->
        <div class="p-4 border-t border-gray-200 bg-gray-50 flex gap-4">
          <el-input v-model="replyText" placeholder="输入回复内容..." class="flex-1" />
          <el-button type="primary">回复</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// 模拟答疑数据
const mockData = Array.from({ length: 25 }).map((_, index) => {
  const isA = index % 2 === 0
  return {
    id: index + 1,
    studentName: isA ? '学生A' : '学生B',
    content: `关于计算机组成原理中流水线CPU的冒险问题，当遇到数据冒险时，除了停顿还有什么处理方法？占位 占位...`,
    replyCount: index % 4,
    time: '2026-07-27 10:00'
  }
})

const currentPage = ref(1)
const pageSize = ref(5)
const total = ref(mockData.length)

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return mockData.slice(start, start + pageSize.value)
})

const detailDialogVisible = ref(false)
const currentDetail = ref<any>(null)
const replyText = ref('')

const handleRowDblclick = (row: any) => {
  currentDetail.value = row
  detailDialogVisible.value = true
  replyText.value = ''
}

// 生成作业逻辑
const targetClass = ref('')
const targetChapter = ref('')
const isGenerating = ref(false)
const generatedContent = ref('')

const generateContent = () => {
  isGenerating.value = true
  setTimeout(() => {
    generatedContent.value = `基于 Agent 生成的作业/考试内容：\n\n一、 选择题\n1. 在一棵度为3的树中，度为3的节点有2个，度为2的节点有1个，度为1的节点有2个，则叶子节点有()个。\n   A. 4\n   B. 5\n   C. 6\n   D. 7\n\n二、 简答题\n1. 请简述图的深度优先搜索(DFS)和广度优先搜索(BFS)的区别与应用场景。\n\n...\n[更多内容由AI自动生成]`
    isGenerating.value = false
  }, 1500)
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

:deep(.el-table tr) {
  cursor: pointer;
}
</style>