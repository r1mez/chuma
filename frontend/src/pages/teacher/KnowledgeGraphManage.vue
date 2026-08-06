<template>
  <div class="kg-manage-page">
    <div class="page-header">
      <h2>知识图谱管理</h2>
      <span class="subtitle">管理所有已构建的知识图谱，点击学科行查看并编辑知识图谱</span>
    </div>

    <div class="kg-manage-layout">
      <!-- 左侧：学科列表 -->
      <div class="kg-manage-left">
        <el-table
          ref="tableRef"
          :data="store.graphList"
          v-loading="store.graphListLoading"
          stripe
          style="width: 100%"
          highlight-current-row
          @current-change="handleRowChange"
          :row-class-name="rowClassName"
        >
          <el-table-column prop="original_filename" label="文件名" min-width="160" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="node_count" label="节点" width="60" />
          <el-table-column prop="edge_count" label="边" width="60" />
          <el-table-column label="操作" width="70" fixed="right">
            <template #default="{ row }">
              <el-button
                type="danger"
                plain
                size="small"
                :disabled="row.status === 'pending'"
                @click.stop="handleDelete(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 右侧：图谱编辑区 -->
      <div class="kg-manage-right" v-if="currentGraph">
        <KgEditorToolbar
          v-model:toolMode="toolMode"
          v-model:visibleTypes="visibleTypes"
          :graphStats="graphData?.stats ?? null"
          @zoom-in="canvasRef?.zoomIn()"
          @zoom-out="canvasRef?.zoomOut()"
          @fit-view="canvasRef?.fitView()"
        />
        <div class="kg-editor-main">
          <div class="kg-editor-canvas-wrapper" v-loading="graphLoading">
            <KgEditorCanvas
              ref="canvasRef"
              :data="graphData"
              :toolMode="toolMode"
              :visibleTypes="visibleTypes"
              @node-selected="onNodeSelected"
              @edge-selected="onEdgeSelected"
              @canvas-click="onCanvasClick"
              @edge-created="onEdgeCreated"
            />
          </div>
          <KgEditorPanel
            :mode="panelMode"
            :isNew="isNewItem"
            :graphName="currentGraph.graph_name"
            :graphStats="graphData?.stats ?? null"
            :selectedNode="selectedNode"
            :selectedEdge="selectedEdge"
            @cancel-edit="onCancelEdit"
            @node-saved="onNodeSaved"
            @node-deleted="onNodeDeleted"
            @edge-saved="onEdgeSaved"
            @edge-deleted="onEdgeDeleted"
          />
        </div>
      </div>

      <!-- 右侧空状态 -->
      <div class="kg-manage-right kg-manage-empty" v-else>
        <el-empty description="请从左侧选择一个学科查看知识图谱" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'
import { fetchGraphStats, fetchGraphData, type KgGraphInfo, type GraphData } from '@/api/knowledge'
import KgEditorToolbar from '@/components/kg-editor/KgEditorToolbar.vue'
import KgEditorCanvas from '@/components/kg-editor/KgEditorCanvas.vue'
import KgEditorPanel from '@/components/kg-editor/KgEditorPanel.vue'
import type { NodeEditData, EdgeEditData } from '@/components/kg-editor/KgEditorCanvas.vue'

const store = useKnowledgeStore()

// ---- 学科选择状态 ----
const currentGraph = ref<KgGraphInfo | null>(null)
const graphData = ref<GraphData | null>(null)
const graphLoading = ref(false)

// ---- 编辑交互状态 ----
const toolMode = ref<'select' | 'add-node' | 'add-edge'>('select')
const visibleTypes = ref<Set<string>>(new Set())
const panelMode = ref<'overview' | 'node' | 'edge'>('overview')
const isNewItem = ref(false)
const selectedNode = ref<NodeEditData | null>(null)
const selectedEdge = ref<EdgeEditData | null>(null)

// ---- Canvas ref ----
const canvasRef = ref<InstanceType<typeof KgEditorCanvas>>()

// ---- Table ref ----
const tableRef = ref()

// ---- beforeunload 提示 ----

function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (isNewItem.value) {
    e.preventDefault()
  }
}

// ---- 初始化 ----

onMounted(() => {
  store.loadGraphList()
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// ---- 学科行点击 ----

async function handleRowChange(row: KgGraphInfo | null) {
  // Null row means deselection — clear graph view
  if (!row) {
    currentGraph.value = null
    graphData.value = null
    return
  }

  if (row.status !== 'completed') {
    // Only allow viewing completed graphs; reset table highlight for rejected rows
    ElMessage.info('该图谱正在构建中，暂不可查看')
    tableRef.value?.setCurrentRow(null)
    return
  }

  // 检查是否有未保存的编辑
  if (isNewItem.value) {
    try {
      await ElMessageBox.confirm(
        '当前有未保存的修改，是否放弃？',
        '提示',
        { confirmButtonText: '放弃', cancelButtonText: '留下', type: 'warning' },
      )
    } catch {
      return
    }
  }

  currentGraph.value = row
  await loadGraph(row.graph_name)
}

async function loadGraph(graphName: string) {
  graphLoading.value = true
  panelMode.value = 'overview'
  selectedNode.value = null
  selectedEdge.value = null
  isNewItem.value = false
  toolMode.value = 'select'

  try {
    const data = await fetchGraphData(graphName)
    if (!data.nodes || data.nodes.length === 0) {
      graphData.value = null
      ElMessage.info('该图谱暂无数据')
    } else {
      graphData.value = data
      // 初始化类型筛选：全部勾选
      visibleTypes.value = new Set()
    }
  } catch {
    graphData.value = null
    ElMessage.error('加载图谱数据失败')
  } finally {
    graphLoading.value = false
  }
}

// ---- 表格行高亮 ----

function rowClassName({ row }: { row: KgGraphInfo }) {
  return currentGraph.value?.id === row.id ? 'current-row' : ''
}

// ---- 选中事件 ----

function onNodeSelected(node: NodeEditData | null) {
  selectedNode.value = node
  selectedEdge.value = null
  isNewItem.value = false
  panelMode.value = node ? 'node' : 'overview'
}

function onEdgeSelected(edge: EdgeEditData | null) {
  selectedEdge.value = edge
  selectedNode.value = null
  isNewItem.value = false
  panelMode.value = edge ? 'edge' : 'overview'
}

function onCanvasClick(coords: { x: number; y: number }) {
  // In add-edge mode, show the edge creation panel directly
  if (toolMode.value === 'add-edge') {
    selectedEdge.value = {
      id: '',
      source: '',
      target: '',
      sourceName: '',
      targetName: '',
      relationship_name: '相关',
      description: '',
    }
    selectedNode.value = null
    isNewItem.value = true
    panelMode.value = 'edge'
    toolMode.value = 'select'
    return
  }

  if (toolMode.value === 'add-node') {
    // 添加节点模式：在点击位置创建临时节点
    const tempId = `temp_${Date.now()}`
    canvasRef.value?.addTempNode(coords.x, coords.y, tempId)
    selectedNode.value = { id: tempId, name: '新节点', type: 'Concept', description: '' }
    selectedEdge.value = null
    isNewItem.value = true
    panelMode.value = 'node'
    return
  }
  // 选择模式：取消选中
  selectedNode.value = null
  selectedEdge.value = null
  isNewItem.value = false
  panelMode.value = 'overview'
}

function onEdgeCreated(_edgeData: any) {
  // ECharts 版本：不再通过拖拽连线创建边
  // 改为在面板中手动选择源/目标节点
  // 此事件保留但不再由 ECharts 触发
}

function onCancelEdit() {
  // 如果是新增的临时节点/边，从画布移除
  if (isNewItem.value && selectedNode.value?.id.startsWith('temp_')) {
    canvasRef.value?.removeItemById(selectedNode.value.id, 'node')
  }
  if (isNewItem.value && selectedEdge.value) {
    canvasRef.value?.removeItemById(selectedEdge.value.id, 'edge')
  }
  selectedNode.value = null
  selectedEdge.value = null
  isNewItem.value = false
  panelMode.value = 'overview'
  toolMode.value = 'select'
  canvasRef.value?.resetHighlight()
}

// ---- 保存/删除回调 ----

function onNodeSaved(data: NodeEditData) {
  if (isNewItem.value && selectedNode.value?.id.startsWith('temp_')) {
    // 新增节点：后端已分配真实 ID，需要重新加载图谱数据
    if (currentGraph.value) {
      loadGraph(currentGraph.value.graph_name)
    }
  } else if (selectedNode.value) {
    // 编辑节点：更新画布上的数据
    canvasRef.value?.updateNodeData(selectedNode.value.id, data)
  }
  selectedNode.value = data
  isNewItem.value = false
  toolMode.value = 'select'
}

function onNodeDeleted(nodeId: string) {
  // 移除关联边
  const relatedEdges = canvasRef.value?.getRelatedEdges(nodeId) || []
  relatedEdges.forEach(edgeId => {
    canvasRef.value?.removeItemById(edgeId, 'edge')
  })
  // 移除节点
  canvasRef.value?.removeItemById(nodeId, 'node')
  selectedNode.value = null
  panelMode.value = 'overview'
  canvasRef.value?.resetHighlight()
}

function onEdgeSaved(data: EdgeEditData) {
  if (isNewItem.value) {
    // 新增边：重新加载图谱数据
    if (currentGraph.value) {
      loadGraph(currentGraph.value.graph_name)
    }
  } else if (selectedEdge.value) {
    canvasRef.value?.updateEdgeData(selectedEdge.value.id, {
      relationship_name: data.relationship_name,
      description: data.description,
    })
  }
  selectedEdge.value = data
  isNewItem.value = false
  toolMode.value = 'select'
}

function onEdgeDeleted(source: string, target: string) {
  const edgeId = `${source}-${target}`
  canvasRef.value?.removeItemById(edgeId, 'edge')
  selectedEdge.value = null
  panelMode.value = 'overview'
  canvasRef.value?.resetHighlight()
}

// ---- 删除图谱（保留原有功能） ----

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
    if (currentGraph.value?.id === row.id) {
      currentGraph.value = null
      graphData.value = null
    }
    ElMessage.success(`已删除 "${row.original_filename}"`)
  } catch (e: any) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(`删除失败: ${e?.message || e}`)
  }
}

// ---- 快捷键 ----

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Delete' || e.key === 'Backspace') {
    // 避免在输入框中触发
    if ((e.target as HTMLElement)?.tagName === 'INPUT' || (e.target as HTMLElement)?.tagName === 'TEXTAREA') return
    if (selectedNode.value && !isNewItem.value) {
      handleDeleteNode()
    } else if (selectedEdge.value && !isNewItem.value) {
      handleDeleteEdge()
    }
  }
  if (e.key === 'Escape') {
    onCancelEdit()
  }
}

async function handleDeleteNode() {
  if (!selectedNode.value || !currentGraph.value) return
  try {
    await ElMessageBox.confirm(
      `确认删除节点 "${selectedNode.value.name}"？\n该节点的所有关联边也将被删除，此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }

  try {
    const { deleteNode } = await import('@/api/knowledge')
    await deleteNode(currentGraph.value.graph_name, selectedNode.value.id)
    onNodeDeleted(selectedNode.value.id)
    ElMessage.success('节点删除成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleDeleteEdge() {
  if (!selectedEdge.value || !currentGraph.value) return
  try {
    await ElMessageBox.confirm(
      `确认删除关系 "${selectedEdge.value.relationship_name}"？\n此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }

  try {
    const { deleteEdge } = await import('@/api/knowledge')
    await deleteEdge(currentGraph.value.graph_name, selectedEdge.value.source, selectedEdge.value.target)
    onEdgeDeleted(selectedEdge.value.source, selectedEdge.value.target)
    ElMessage.success('关系删除成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.kg-manage-page {
  padding: 24px;
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
}
.page-header {
  margin-bottom: 16px;
  flex-shrink: 0;
}
.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  color: #1f2937;
}
.subtitle {
  font-size: 13px;
  color: #9ca3af;
}
.kg-manage-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}
.kg-manage-left {
  width: 420px;
  min-width: 420px;
  flex-shrink: 0;
  overflow-y: auto;
}
.kg-manage-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.kg-manage-empty {
  align-items: center;
  justify-content: center;
}
.kg-editor-main {
  display: flex;
  flex: 1;
  min-height: 0;
}
.kg-editor-canvas-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
}
</style>
