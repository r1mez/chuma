<template>
  <el-container>
    <el-aside width="200px">
      <el-menu router>
        <el-menu-item index="/student/dashboard">学习仪表盘</el-menu-item>

        <!-- 知识图谱分组 -->
        <el-sub-menu index="kg-group">
          <template #title>🧠 知识图谱</template>

          <el-menu-item index="/student/kg-pipeline">
            <span>📤 图谱构建</span>
          </el-menu-item>

          <el-menu-item
            v-for="graph in graphList"
            :key="graph.id"
            :index="`/student/knowledge?graphId=${graph.id}`"
            class="kg-graph-item"
          >
            <span class="graph-name" :title="graph.original_filename">
              📊 {{ graph.original_filename }}
            </span>
            <span v-if="graph.status === 'failed'" class="status-dot failed" title="构建失败" />
            <span v-else-if="graph.status === 'pending'" class="status-dot pending" title="构建中" />
            <el-icon
              class="delete-btn"
              @click.stop="handleDelete(graph.id, graph.graph_name)"
            >
              <Delete />
            </el-icon>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/student/practice">题目练习</el-menu-item>
        <el-menu-item index="/student/wrong-book">错题本</el-menu-item>
        <el-menu-item index="/student/chat">AI 助教</el-menu-item>
        <el-menu-item index="/student/plan">学习计划</el-menu-item>
        <el-menu-item index="/student/ocr">📄 文档解析</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()
const { graphList, graphListLoading } = storeToRefs(store)

onMounted(() => {
  store.loadGraphList()
})

async function handleDelete(graphId: number, graphName: string) {
  try {
    await ElMessageBox.confirm('确定要删除此知识图谱吗？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.deleteKgGraph(graphId, graphName)
    ElMessage.success('图谱已删除')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.kg-graph-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.kg-graph-item:hover .delete-btn {
  display: inline-flex;
}
.graph-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.delete-btn {
  display: none;
  color: #f56c6c;
  font-size: 14px;
  cursor: pointer;
  margin-left: 4px;
}
.delete-btn:hover {
  color: #e64e4e;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  flex-shrink: 0;
}
.status-dot.failed {
  background: #f56c6c;
}
.status-dot.pending {
  background: #e6a23c;
}
</style>
