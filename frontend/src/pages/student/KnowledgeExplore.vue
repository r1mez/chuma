<template>
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
          <el-button type="primary" @click="store.loadGraphData(store.currentGraphName || undefined)">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- 空状态 -->
    <div v-else-if="store.isEmpty" class="kg-state">
      <el-empty description="还没有构建知识图谱">
        <template #image>
          <div class="empty-graph-icon">🔍</div>
        </template>
        <el-button type="primary" @click="$router.push('/student/kg-pipeline')">
          上传文档构建知识图谱
        </el-button>
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
            @select="(item: any) => focusNode(item.value)"
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

      <!-- 图例 -->
      <div class="kg-legend">
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
      </div>

      <!-- 图容器 + 详情面板 -->
      <div class="kg-chart-wrapper">
        <KnowledgeGraph
          ref="graphRef"
          :data="store.graphData"
          :show-labels="showLabels"
          :active-types="store.activeTypes"
          @node-click="store.selectNode"
        />
        <GraphDetailPanel
          v-if="store.selectedNode"
          :node="store.selectedNode"
          @close="store.selectNode(null)"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Search, ZoomIn, ZoomOut, Refresh } from '@element-plus/icons-vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import GraphDetailPanel from '@/components/GraphDetailPanel.vue'
import { useGraph } from '@/composables/useGraph'

const route = useRoute()
const store = useKnowledgeStore()
const graphRef = ref<InstanceType<typeof KnowledgeGraph>>()
const { showLabels, handleSearch, focusNode, resetView } = useGraph()

const TYPE_COLORS: Record<string, string> = {
  Concept: '#7C3AED', Algorithm: '#F59E0B', DataStructure: '#10B981',
  Protocol: '#3B82F6', Principle: '#EC4899', Term: '#94A3B8',
  Technology: '#06B6D4', Model: '#F97316',
}

function querySearch(query: string, cb: (results: any[]) => void) {
  if (!query.trim()) return cb([])
  handleSearch(query).then(() => {
    const results = (store.graphData?.nodes ?? [])
      .filter(n => n.name.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 10)
      .map(n => ({ value: n.name, nodeId: n.id }))
    cb(results)
  })
}

function zoomIn() { /* ECharts zoom */ }
function zoomOut() { /* ECharts zoom */ }

async function loadGraphByRoute() {
  const graphId = route.query.graphId ? Number(route.query.graphId) : null
  if (graphId) {
    store.currentGraphId = graphId
    const graph = store.graphList.find(g => g.id === graphId)
    if (graph && graph.status === 'completed') {
      await store.loadGraphData(graph.graph_name)
    } else if (graph && graph.status === 'failed') {
      store.error = { type: 'not_found', message: '该图谱构建失败，请重新上传文档' }
    } else {
      store.error = { type: 'not_found', message: '该图谱还没有构建完成' }
    }
  } else {
    // 无参数时自动使用最近完成的图谱
    const recentCompleted = store.graphList.find(g => g.status === 'completed')
    if (recentCompleted) {
      store.currentGraphId = recentCompleted.id
      await store.loadGraphData(recentCompleted.graph_name)
    } else {
      // 没有完成的图谱，使用最近的一个
      const recent = store.graphList[0]
      if (recent) {
        store.currentGraphId = recent.id
        if (recent.status === 'completed') {
          await store.loadGraphData(recent.graph_name)
        } else if (recent.status === 'failed') {
          store.error = { type: 'not_found', message: '该图谱构建失败，请重新上传文档' }
        }
      }
    }
  }
}

// 监听路由变化，切换图谱时自动刷新
watch(() => route.query.graphId, () => {
  loadGraphByRoute()
})

onMounted(async () => {
  await store.loadGraphList()
  await loadGraphByRoute()
})
</script>

<style scoped>
.kg-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0F0F0F;
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
  color: #94A3B8;
  margin-top: 16px;
  font-size: 14px;
}
.kg-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
}
.kg-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94A3B8;
  font-variant-numeric: tabular-nums;
}
.stat-divider { width: 1px; height: 16px; background: #333; }
.kg-search-wrapper { flex: 1; max-width: 320px; }
.kg-controls { display: flex; align-items: center; gap: 12px; }
.kg-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 20px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #94A3B8;
  transition: all 0.2s;
}
.legend-item:hover { background: rgba(255,255,255,0.05); }
.legend-item.inactive { opacity: 0.4; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; }
.kg-chart-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}
</style>
