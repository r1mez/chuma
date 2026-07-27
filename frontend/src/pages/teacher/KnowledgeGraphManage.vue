<template>
  <div class="kg-manage-page">
    <div class="page-header">
      <h2>知识图谱管理</h2>
      <span class="subtitle">管理所有已构建的知识图谱，删除将同时清理关联的切片和 AGE 图数据</span>
    </div>

    <el-table :data="store.graphList" v-loading="store.graphListLoading" stripe style="width: 100%">
      <el-table-column prop="original_filename" label="文件名" min-width="200" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="node_count" label="节点数" width="100" />
      <el-table-column prop="edge_count" label="边数" width="100" />
      <el-table-column prop="chunk_count" label="切片数" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="danger"
            plain
            size="small"
            :disabled="row.status === 'pending'"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'
import { fetchGraphStats, type KgGraphInfo } from '@/api/knowledge'

const store = useKnowledgeStore()

onMounted(() => {
  store.loadGraphList()
})

function statusTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'completed': return 'success'
    case 'pending': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'completed': return '已完成'
    case 'pending': return '构建中'
    case 'failed': return '失败'
    default: return status
  }
}

async function handleDelete(row: KgGraphInfo) {
  try {
    const stats = await fetchGraphStats(row.id)
    await ElMessageBox.confirm(
      `确认删除以下教材的全部数据？\n\n` +
      `教材：${stats.original_filename}\n` +
      `├─ 知识图谱节点：${stats.node_count} 个\n` +
      `├─ 知识图谱边：  ${stats.edge_count} 条\n` +
      `├─ 文档切片：    ${stats.chunk_count} 条\n` +
      `└─ 此操作不可恢复`,
      '确认删除',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
    )
    await store.deleteKgGraph(row.id, row.graph_name)
    ElMessage.success(`已删除 "${row.original_filename}"`)
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(`删除失败: ${e?.message || e}`)
  }
}
</script>

<style scoped>
.kg-manage-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  color: #1f2937;
}
.subtitle {
  font-size: 13px;
  color: #9ca3af;
}
</style>
