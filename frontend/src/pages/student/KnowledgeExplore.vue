<template>
  <BorderGlow class="kg-page" background-color="transparent">
    <!-- 图谱选择器 - 在黑色大框上方 -->
    <div class="kg-header">
      <el-select
        v-model="selectedGraphId"
        placeholder="选择图谱"
        size="default"
        style="width: 260px"
        @change="onGraphSelect"
      >
        <el-option
          v-for="g in store.graphList"
          :key="g.id"
          :label="g.original_filename"
          :value="g.id"
        >
          <span>{{ g.original_filename }}</span>
          <span v-if="g.status === 'failed'" class="graph-status-tag">失败</span>
          <span v-else-if="g.status === 'pending'" class="graph-status-tag pending">构建中</span>
        </el-option>
      </el-select>
      <StarBorder as="div" color="#f56c6c" speed="3s">
        <el-button
          v-if="selectedGraphId"
          type="danger"
          plain
          size="small"
          :icon="Delete"
          @click="handleDelete"
        >
          删除
        </el-button>
      </StarBorder>
    </div>

    <!-- 图谱主体 -->
    <div class="kg-container">
      <!-- 加载状态 -->
      <div v-if="store.loading" class="kg-state">
        <el-skeleton :rows="5" animated />
        <p class="state-text">正在加载知识图谱...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="store.error" class="kg-state">
        <el-result
          icon="error"
          :title="store.error.type === 'network' ? '网络错误' : '加载失败'"
          :sub-title="store.error.message"
        >
          <template #extra>
            <StarBorder as="div" color="#409eff" speed="4s">
              <el-button type="primary" @click="store.loadGraphData(store.currentGraphName || undefined)">重试</el-button>
            </StarBorder>
          </template>
        </el-result>
      </div>

      <!-- 空状态 -->
      <div v-else-if="store.isEmpty" class="kg-state">
        <el-empty description="还没有构建知识图谱">
          <template #image>
            <div class="empty-graph-icon">🔍</div>
          </template>
          <StarBorder as="div" color="#409eff" speed="5s">
            <el-button type="primary" @click="$router.push('/student/kg-pipeline')">
              上传文档构建知识图谱
            </el-button>
          </StarBorder>
        </el-empty>
      </div>

      <!-- 图谱视图 -->
      <template v-else-if="store.graphData">
        <div class="kg-toolbar">
          <div class="kg-stats">
            <span class="stat-item">节点: {{ store.nodeCount }}</span>
            <span class="stat-divider" />
            <span class="stat-item">边: {{ store.edgeCount }}</span>
          </div>
          <div class="kg-search-wrapper">
            <el-autocomplete
              v-model="store.searchQuery"
              :fetch-suggestions="querySearch"
              placeholder="搜索实体..."
              :prefix-icon="Search"
              clearable
              size="small"
              @select="onSearchSelect"
            />
          </div>
          <div class="kg-controls">
            <el-switch v-model="showLabels" active-text="标签" size="small" />
            <el-button-group size="small">
              <el-button :icon="ZoomIn" @click="zoomIn" />
              <el-button :icon="ZoomOut" @click="zoomOut" />
              <el-button :icon="Refresh" @click="resetView" />
            </el-button-group>
          </div>
        </div>

        <!-- 面包屑导航 -->
        <div v-if="drillPath.length > 0" class="kg-breadcrumb">
          <span class="breadcrumb-item" @click="drillPath = []">全部章节</span>
          <template v-for="(node, idx) in drillPath" :key="node.id">
            <span class="breadcrumb-sep">&gt;</span>
            <span
              class="breadcrumb-item"
              :class="{ active: idx === drillPath.length - 1 }"
              @click="drillPath = drillPath.slice(0, idx + 1)"
            >
              {{ node.name }}
            </span>
          </template>
        </div>

        <!-- 图例 -->
        <div class="kg-legend">
          <template v-if="isKnowledgePointLevel">
            <div
              v-for="(color, type) in TYPE_COLORS"
              :key="type"
              class="legend-item"
              :class="{ inactive: store.activeTypes.has(type) }"
              @click="store.toggleType(type)"
            >
              <span class="legend-dot" :style="{ background: color }" />
              <span class="legend-label">{{ type }}</span>
            </div>
          </template>
          <template v-else>
            <div class="legend-item" style="cursor: default">
              <span class="legend-dot" :style="{ background: '#6366F1' }" />
              <span class="legend-label">Chapter</span>
            </div>
          </template>
        </div>

        <!-- 图容器 + 详情面板 -->
        <div class="kg-chart-wrapper">
          <KnowledgeGraph
            ref="graphRef"
            :data="currentGraphData!"
            :show-labels="showLabels"
            :active-types="store.activeTypes"
            :expanded-node-ids="allExpandedNodeIds"
            :anchor-node-ids="anchorNodeIds"
            @node-click="handleNodeClick"
            @node-dbl-click="handleNodeDblClick"
          />
          <GraphDetailPanel
            v-if="store.selectedNode"
            :node="store.selectedNode"
            @close="store.selectNode(null)"
          />
          <!-- 知识点层空状态 -->
          <div
            v-if="isKnowledgePointLevel && currentGraphData && currentGraphData.nodes.length <= 1"
            class="kg-empty-overlay"
          >
            <div class="kg-empty-text">
              <span class="empty-icon">📭</span>
              <p>该节暂无知识点</p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </BorderGlow>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, ZoomIn, ZoomOut, Refresh, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import GraphDetailPanel from '@/components/GraphDetailPanel.vue'
import { useGraph } from '@/composables/useGraph'
import StarBorder from '@/components/StarBorder.vue'
import BorderGlow from '@/components/BorderGlow.vue'

import { parseHierarchy, getVisibleData, tryDrillInto } from '@/utils/kgHierarchy'
import type { GraphNode, GraphData } from '@/api/knowledge'

const route = useRoute()
const $router = useRouter()
const store = useKnowledgeStore()
const graphRef = ref<InstanceType<typeof KnowledgeGraph>>()
const { showLabels, handleSearch, resetView } = useGraph()
const selectedGraphId = ref<number | null>(null)

// 钻取状态
const drillPath = ref<GraphNode[]>([])

// 双击展开状态：nodeId → 因该节点展开而加入的节点 ID 集合
const expandedNodeMap = ref<Map<string, Set<string>>>(new Map())

// 引用计数：nodeId → 被多少个展开锚点引用
const expandedRefCount = computed(() => {
  const counter = new Map<string, number>()
  for (const addedNodes of expandedNodeMap.value.values()) {
    for (const nodeId of addedNodes) {
      counter.set(nodeId, (counter.get(nodeId) || 0) + 1)
    }
  }
  return counter
})

// 所有因展开而加入的节点 ID（去重）
const allExpandedNodeIds = computed(() => new Set(expandedRefCount.value.keys()))

// 当前展开操作的锚点节点（被双击的节点）
const anchorNodeIds = computed(() => new Set(expandedNodeMap.value.keys()))

// 钻取路径改变时清空展开状态
watch(drillPath, () => {
  expandedNodeMap.value = new Map()
})

const TYPE_COLORS: Record<string, string> = {
  Concept: '#7C3AED', Algorithm: '#F59E0B', DataStructure: '#10B981',
  Protocol: '#3B82F6', Principle: '#EC4899', Term: '#94A3B8',
  Technology: '#06B6D4', Model: '#F97316',
}

// 层级结构（依赖 store.graphData）
const hierarchy = computed(() => {
  if (!store.graphData) return null
  return parseHierarchy(store.graphData)
})

// 当前层级应展示的图谱数据（含展开节点）
const currentGraphData = computed<GraphData | null>(() => {
  if (!store.graphData || !hierarchy.value) return store.graphData
  const base = getVisibleData(store.graphData, drillPath.value, hierarchy.value)

  // 如果没有展开的节点，直接返回基础数据
  if (expandedNodeMap.value.size === 0) return base

  // 合并展开节点
  const baseNodeIds = new Set(base.nodes.map(n => n.id))
  const mergedNodes = [...base.nodes]

  for (const nodeId of allExpandedNodeIds.value) {
    if (!baseNodeIds.has(nodeId)) {
      const fullNode = hierarchy.value.nodeMap.get(nodeId)
      if (fullNode) mergedNodes.push(fullNode)
    }
  }

  const mergedNodeIds = new Set(mergedNodes.map(n => n.id))
  const mergedEdges = store.graphData.edges.filter(
    e => mergedNodeIds.has(e.source) && mergedNodeIds.has(e.target)
  )

  const typeCounter: Record<string, number> = {}
  for (const n of mergedNodes) {
    typeCounter[n.type] = (typeCounter[n.type] || 0) + 1
  }

  return {
    nodes: mergedNodes,
    edges: mergedEdges,
    stats: {
      total_nodes: mergedNodes.length,
      total_edges: mergedEdges.length,
      node_types: typeCounter,
    },
  }
})

// 是否在知识点层（控制图例和类型筛选）
const isKnowledgePointLevel = computed(() => {
  if (drillPath.value.length === 0) return false
  const currentChapter = drillPath.value[drillPath.value.length - 1]
  const subSections = hierarchy.value?.chapterChildren.get(currentChapter.id)
  // 知识点层：depth===2 或 depth===1 但无子节
  return drillPath.value.length === 2 || (drillPath.value.length === 1 && (subSections?.length || 0) === 0)
})

function handleNodeClick(node: GraphNode) {
  if (!hierarchy.value) return

  const newPath = tryDrillInto(node, drillPath.value, hierarchy.value)
  if (newPath !== null) {
    // Chapter 节点 → 钻取
    drillPath.value = newPath
    store.selectNode(null) // 关闭详情面板
  } else {
    // 知识点节点 → 显示详情面板（保持现有行为）
    store.selectNode(node)
  }
}

function handleNodeDblClick(node: GraphNode) {
  if (!hierarchy.value || !store.graphData) return

  // 如果已展开 → 收起
  if (expandedNodeMap.value.has(node.id)) {
    const newMap = new Map(expandedNodeMap.value)
    newMap.delete(node.id)
    expandedNodeMap.value = newMap
    return
  }

  // 展开：BFS 向外找 3 跳的所有连通知识点（跨章节）
  const kpTypes = new Set(['Concept', 'Algorithm', 'DataStructure', 'Protocol', 'Principle', 'Term', 'Technology', 'Model'])

  // 建立邻接表
  const adj = new Map<string, string[]>()
  for (const edge of store.graphData.edges) {
    if (!adj.has(edge.source)) adj.set(edge.source, [])
    if (!adj.has(edge.target)) adj.set(edge.target, [])
    adj.get(edge.source)!.push(edge.target)
    adj.get(edge.target)!.push(edge.source)
  }

  // BFS 2 跳（遍历所有节点类型以正确计算步数，但只收集知识点节点）
  const visited = new Set<string>([node.id])
  const queue: string[] = [node.id]
  const collected = new Set<string>()
  let distance = 0

  while (queue.length > 0 && distance < 1) {
    const levelSize = queue.length
    for (let i = 0; i < levelSize; i++) {
      const cur = queue.shift()!
      const neighbors = adj.get(cur) || []
      for (const nb of neighbors) {
        if (!visited.has(nb)) {
          visited.add(nb)
          queue.push(nb)
          const nbNode = hierarchy.value.nodeMap.get(nb)
          if (nbNode && kpTypes.has(nbNode.type) && nb !== node.id) {
            collected.add(nb)
          }
        }
      }
    }
    distance++
  }

  const newMap = new Map(expandedNodeMap.value)
  newMap.set(node.id, collected)
  expandedNodeMap.value = newMap
}

function querySearch(query: string, cb: (results: any[]) => void) {
  if (!query.trim()) return cb([])
  handleSearch(query).then(() => {
    const data = currentGraphData.value
    const results = (data?.nodes ?? [])
      .filter((n: { name: string }) => n.name.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 10)
      .map((n: { name: string; id: string }) => ({ value: n.name, nodeId: n.id }))
    cb(results)
  })
}

function onSearchSelect(item: { value: string; nodeId: string }) {
  const data = currentGraphData.value
  const node = data?.nodes.find((n: { id: string }) => n.id === item.nodeId)
  if (node) {
    handleNodeClick(node)
  }
}

function zoomIn() { /* ECharts zoom */ }
function zoomOut() { /* ECharts zoom */ }

function onGraphSelect(graphId: number) {
  drillPath.value = []  // 切换图谱时重置钻取路径
  const graph = store.graphList.find(g => g.id === graphId)
  if (graph && graph.status === 'completed') {
    $router.push({ query: { graphId } })
  }
}

async function handleDelete() {
  if (!selectedGraphId.value) return
  const graph = store.graphList.find(g => g.id === selectedGraphId.value)
  if (!graph) return
  try {
    await ElMessageBox.confirm(
      `确定要删除图谱"${graph.original_filename}"吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await store.deleteKgGraph(graph.id, graph.graph_name)
    ElMessage.success('图谱已删除')
    selectedGraphId.value = null
  } catch {
    // 用户取消
  }
}

async function loadGraphByRoute() {
  const graphId = route.query.graphId ? Number(route.query.graphId) : null
  if (graphId) {
    store.currentGraphId = graphId
    selectedGraphId.value = graphId
    const graph = store.graphList.find(g => g.id === graphId)
    if (graph && graph.status === 'completed') {
      await store.loadGraphData(graph.graph_name)
    } else if (graph && graph.status === 'failed') {
      store.error = { type: 'not_found', message: '该图谱构建失败，请重新上传文档' }
    } else {
      store.error = { type: 'not_found', message: '该图谱还没有构建完成' }
    }
  } else {
    const recentCompleted = store.graphList.find(g => g.status === 'completed')
    if (recentCompleted) {
      store.currentGraphId = recentCompleted.id
      selectedGraphId.value = recentCompleted.id
      await store.loadGraphData(recentCompleted.graph_name)
    } else {
      const recent = store.graphList[0]
      if (recent) {
        store.currentGraphId = recent.id
        selectedGraphId.value = recent.id
        if (recent.status === 'completed') {
          await store.loadGraphData(recent.graph_name)
        } else if (recent.status === 'failed') {
          store.error = { type: 'not_found', message: '该图谱构建失败，请重新上传文档' }
        }
      }
    }
  }
}

watch(() => route.query.graphId, () => {
  drillPath.value = []
  loadGraphByRoute()
})

onMounted(async () => {
  await store.loadGraphList()
  drillPath.value = []
  await loadGraphByRoute()
})
</script>

<style scoped>
:deep(.el-empty__description p) { color: #080808; }
:deep(.el-result__title p) { color: #1f2937; }
:deep(.el-result__subtitle p) { color: #6b7280; }
:deep(.el-select__wrapper) { background: rgba(255, 255, 255, 0.5); border-color: rgba(0, 0, 0, 0.1); color: #1f2937; }
:deep(.el-input__inner) { color: #1f2937; }
.kg-page {
  height: calc(100vh - 170px);
  margin: 16px;
}
.kg-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 4px;
  margin-bottom: 12px;
}
.graph-status-tag {
  color: #f56c6c;
  margin-left: 8px;
  font-size: 12px;
}
.graph-status-tag.pending {
  color: #e6a23c;
}
.kg-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  overflow: hidden;
}
.kg-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 48px;
}
.state-text {
  color: #4b5563;
  margin-top: 16px;
  font-size: 14px;
}
.kg-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.kg-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #4b5563;
  font-variant-numeric: tabular-nums;
}
.stat-divider { width: 1px; height: 16px; background: #d1d5db; }
.kg-search-wrapper { flex: 1; max-width: 320px; }
.kg-controls { display: flex; align-items: center; gap: 12px; }
.kg-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 20px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #4b5563;
  transition: all 0.2s;
}
.legend-item:hover { background: rgba(0,0,0,0.05); }
.legend-item.inactive { opacity: 0.4; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; }
.kg-chart-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}
.kg-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: rgba(15, 15, 15, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 13px;
}
.breadcrumb-item {
  color: #94A3B8;
  cursor: pointer;
  transition: color 0.2s;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.breadcrumb-item:hover {
  color: #F4F4F4;
}
.breadcrumb-item.active {
  color: #F4F4F4;
  font-weight: 600;
}
.breadcrumb-sep {
  color: #555;
  font-size: 11px;
}

.kg-empty-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 15, 15, 0.6);
  backdrop-filter: blur(2px);
  z-index: 50;
  pointer-events: none;
}
.kg-empty-text {
  text-align: center;
  color: #94A3B8;
}
.kg-empty-text .empty-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
}
.kg-empty-text p {
  margin: 0;
  font-size: 14px;
}
</style>