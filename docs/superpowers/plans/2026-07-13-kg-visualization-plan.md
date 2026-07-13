# 知识图谱可视化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在前端新增一个交互式知识图谱可视化页面，后端提供图数据 API，参照 Cognee 的暗色力导向图风格。

**Architecture:** 后端新增 AGE Cypher 查询层 → REST API → 前端 ECharts Force Graph 渲染。后端无状态查询，前端全量加载后本地交互。

**Tech Stack:** Python 3.11+, FastAPI, AGE (Cypher), Vue 3, TypeScript, ECharts 5, Element Plus, Pinia

## 全局约束

- 后端：所有 AGE 查询通过 `ai/app/kg_pipeline/storage.py` 的 `AgeStorage._get_conn()` 连接
- 前端：ECharts 5 （已在 package.json），Element Plus 组件库
- 前端 API 调用通过已有的 `@/utils/request`（Axios 封装，自动注入 JWT）
- 不修改 router（`/student/knowledge` 路由已存在）
- 不修改已有的 KG pipeline 代码（queries.py 是只读查询，不涉及写入）

---

## 文件结构概览

```
# 后端（新建 + 修改）
ai/app/kg_pipeline/queries.py      # 新建：AGE 只读查询封装
ai/app/api/kg.py                    # 修改：新增 graph/data, graph/search 端点

# 前端 API / Store（修改已有文件）
frontend/src/api/knowledge.ts       # 修改：新增 fetchGraphData, searchNodes
frontend/src/stores/knowledge.ts    # 修改：扩展完整状态管理

# 前端组件（新建 + 修改）
frontend/src/components/KnowledgeGraph.vue     # 新建：ECharts 力导向图组件
frontend/src/components/GraphDetailPanel.vue   # 新建：节点详情面板
frontend/src/composables/useGraph.ts           # 新建：图交互组合式函数
frontend/src/pages/student/KnowledgeExplore.vue  # 修改：完整实现
```

---

### Task 1：AGE 查询封装 (queries.py)

**Files:**
- Create: `ai/app/kg_pipeline/queries.py`

**Interfaces:**
- Produces: `get_full_graph(dataset_id: str) -> tuple[list, list, dict]`
- Produces: `search_nodes(query: str, dataset_id: str) -> list`
- Consumes: `AgeStorage._get_conn()` (via `app.kg_pipeline.storage`)

- [ ] **Step 1: Write queries.py**

```python
"""AGE 图数据只读查询封装

为 API 层提供结构化的图数据读取接口。
通过 AgeStorage 的连接池读取 AGE，不涉及写入操作。
"""

import logging
from typing import Any

from app.kg_pipeline.storage import AgeStorage, AgeConnectionError


logger = logging.getLogger(__name__)


class GraphQueryError(Exception):
    """图数据查询失败"""
    pass


def get_full_graph(dataset_id: str = "main") -> dict[str, Any]:
    """获取完整图数据（节点 + 边 + 统计）

    Returns:
        {
            "nodes": [{"id", "name", "type", "description", "degree"}, ...],
            "edges": [{"source", "target", "relationship_name", "description"}, ...],
            "stats": {"total_nodes": int, "total_edges": int, "node_types": {...}}
        }
    """
    storage = AgeStorage()

    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e

    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO ag_catalog, public;")

            # 查询所有节点
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) RETURN n.id, n.name, n.type, n.description "
                f"$$) AS (id text, name text, type text, description text)"
            )
            rows = cur.fetchall()

            nodes = []
            type_counter: dict[str, int] = {}
            for row in rows:
                nid, name, ntype, desc = row
                nodes.append({
                    "id": nid,
                    "name": name or nid,
                    "type": ntype or "Concept",
                    "description": desc or "",
                    "degree": 0,
                })
                t = ntype or "Concept"
                type_counter[t] = type_counter.get(t, 0) + 1

            # 查询所有边
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (a:Entity)-[r:RELATION]->(b:Entity) "
                f"RETURN a.id, b.id, r.relationship_name, r.description "
                f"$$) AS (source text, target text, rel text, desc text)"
            )
            edge_rows = cur.fetchall()

            edges = []
            degree_counter: dict[str, int] = {}
            for row in edge_rows:
                src, tgt, rel, desc = row
                edges.append({
                    "source": src,
                    "target": tgt,
                    "relationship_name": rel or "related_to",
                    "description": desc or "",
                })
                degree_counter[src] = degree_counter.get(src, 0) + 1
                degree_counter[tgt] = degree_counter.get(tgt, 0) + 1

            # 回填节点 degree
            for node in nodes:
                node["degree"] = degree_counter.get(node["id"], 0)

    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise GraphQueryError(str(e)) from e
    finally:
        conn.close()

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": type_counter,
        },
    }


def search_nodes(query: str, dataset_id: str = "main") -> list[dict]:
    """按名称搜索实体

    Returns:
        [{"id", "name", "type", "description"}, ...]
    """
    storage = AgeStorage()

    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e

    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO ag_catalog, public;")
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) "
                f"WHERE toLower(n.name) CONTAINS toLower('{_escape(query)}') "
                f"RETURN n.id, n.name, n.type, n.description "
                f"LIMIT 20 "
                f"$$) AS (id text, name text, type text, description text)"
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise GraphQueryError(str(e)) from e
    finally:
        conn.close()

    return [
        {"id": r[0], "name": r[1], "type": r[2], "description": r[3]}
        for r in rows
    ]


def _escape(value: str) -> str:
    """转义 Cypher 字符串中的单引号和反斜杠"""
    return value.replace("\\", "\\\\").replace("'", "\\'")
```

- [ ] **Step 2: Verify imports**

```bash
cd G:/dev/chuma/ai && python -c "from app.kg_pipeline.queries import get_full_graph, search_nodes; print('queries OK')"
```

Expected: `queries OK`

---

### Task 2：后端 API 端点

**Files:**
- Modify: `ai/app/api/kg.py`

- [ ] **Step 1: Read current kg.py and append new endpoints**

Append after the existing `/build/result/{task_id}` endpoint:

```python
from app.kg_pipeline.queries import get_full_graph, search_nodes, GraphQueryError


@router.get("/graph/data")
async def get_graph_data(dataset_id: str = "main"):
    """获取知识图谱全量数据（节点 + 边 + 统计）"""
    try:
        data = await asyncio.get_event_loop().run_in_executor(
            None, get_full_graph, dataset_id
        )
        return data
    except GraphQueryError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/graph/search")
async def search_graph_nodes(q: str, dataset_id: str = "main"):
    """按名称搜索实体节点"""
    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, search_nodes, q, dataset_id
        )
        return {"results": results}
    except GraphQueryError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

Note: `get_full_graph` and `search_nodes` are synchronous (psycopg2 is sync), so we wrap them in `run_in_executor` to avoid blocking the async event loop.

Also add the `import asyncio` at the top of the file.

- [ ] **Step 2: Verify**

```bash
cd G:/dev/chuma/ai && python -c "from app.api.kg import router; print('kg API with graph endpoints OK')"
```

Expected: `kg API with graph endpoints OK`

---

### Task 3：前端 API 层 + Store

**Files:**
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/stores/knowledge.ts`

- [ ] **Step 1: Write frontend/src/api/knowledge.ts**

```typescript
import request from '@/utils/request'

export interface GraphNode {
  id: string
  name: string
  type: string
  description: string
  degree: number
}

export interface GraphEdge {
  source: string
  target: string
  relationship_name: string
  description?: string
}

export interface GraphStats {
  total_nodes: number
  total_edges: number
  node_types: Record<string, number>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: GraphStats
}

export interface SearchResult {
  results: Array<{
    id: string
    name: string
    type: string
    description: string
  }>
}

export async function fetchGraphData(datasetId = 'main'): Promise<GraphData> {
  return request.get('/kg/graph/data', { params: { dataset_id: datasetId } })
}

export async function searchNodes(query: string, datasetId = 'main'): Promise<SearchResult> {
  return request.get('/kg/graph/search', { params: { q: query, dataset_id: datasetId } })
}
```

- [ ] **Step 2: Write frontend/src/stores/knowledge.ts**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchGraphData, searchNodes, type GraphData, type GraphNode } from '@/api/knowledge'

export type GraphErrorType =
  | { type: 'network'; message: string }
  | { type: 'not_found'; message: string }
  | { type: 'server'; message: string }

export const useKnowledgeStore = defineStore('knowledge', () => {
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<GraphErrorType | null>(null)
  const selectedNode = ref<GraphNode | null>(null)
  const searchQuery = ref('')
  const activeTypes = ref<Set<string>>(new Set())

  const isEmpty = computed(() => !loading.value && !error.value && !graphData.value)
  const nodeCount = computed(() => graphData.value?.stats.total_nodes ?? 0)
  const edgeCount = computed(() => graphData.value?.stats.total_edges ?? 0)

  async function loadGraphData(datasetId = 'main') {
    loading.value = true
    error.value = null
    try {
      const data = await fetchGraphData(datasetId)
      if (!data.nodes || data.nodes.length === 0) {
        graphData.value = null
        error.value = { type: 'not_found', message: '该数据集还没有图谱数据' }
      } else {
        graphData.value = data
      }
    } catch (e: any) {
      if (e.message?.includes?.('Network') || e.code === 'ERR_NETWORK') {
        error.value = { type: 'network', message: '无法连接服务器' }
      } else {
        error.value = { type: 'server', message: e?.message || '服务端错误' }
      }
    } finally {
      loading.value = false
    }
  }

  async function searchNodesByQuery(query: string) {
    searchQuery.value = query
    if (!query.trim()) return
    try {
      const result = await searchNodes(query)
      return result.results
    } catch {
      return []
    }
  }

  function selectNode(node: GraphNode | null) {
    selectedNode.value = node
  }

  function toggleType(type: string) {
    const set = new Set(activeTypes.value)
    if (set.has(type)) set.delete(type)
    else set.add(type)
    activeTypes.value = set
  }

  return {
    graphData, loading, error, selectedNode, searchQuery, activeTypes,
    isEmpty, nodeCount, edgeCount,
    loadGraphData, searchNodesByQuery, selectNode, toggleType,
  }
})
```

---

### Task 4：ECharts 图组件 (KnowledgeGraph.vue)

**Files:**
- Create: `frontend/src/components/KnowledgeGraph.vue`

- [ ] **Step 1: Create KnowledgeGraph.vue**

```vue
<template>
  <div ref="chartRef" class="kg-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode, GraphEdge } from '@/api/knowledge'
import { useKnowledgeStore } from '@/stores/knowledge'

const props = defineProps<{
  data: GraphData
  showLabels: boolean
  activeTypes: Set<string>
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
}>()

const store = useKnowledgeStore()
const chartRef = ref<HTMLElement>()
const chart = shallowRef<echarts.ECharts>()

// Cognee 风格颜色映射
const TYPE_COLORS: Record<string, string> = {
  Concept: '#7C3AED',
  Algorithm: '#F59E0B',
  DataStructure: '#10B981',
  Protocol: '#3B82F6',
  Principle: '#EC4899',
  Term: '#94A3B8',
  Technology: '#06B6D4',
  Model: '#F97316',
}

function getColor(type: string): string {
  return TYPE_COLORS[type] || '#94A3B8'
}

function buildOption() {
  const filteredNodes = props.data.nodes.filter(
    n => props.activeTypes.size === 0 || props.activeTypes.has(n.type)
  )
  const activeNodeIds = new Set(filteredNodes.map(n => n.id))
  const filteredEdges = props.data.edges.filter(
    e => activeNodeIds.has(e.source) && activeNodeIds.has(e.target)
  )

  return {
    backgroundColor: '#0F0F0F',
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const n = params.data
          return `
            <div style="font-weight:600;margin-bottom:4px">${n.name}</div>
            <span style="display:inline-block;padding:0 6px;border-radius:4px;
              background:${getColor(n.value)};color:#fff;font-size:11px">${n.value}</span>
            <p style="margin:6px 0 0;font-size:12px;color:#aaa">${n.description || ''}</p>
          `
        }
        return ''
      },
      backgroundColor: '#1a1a2e',
      borderColor: '#333',
      textStyle: { color: '#F4F4F4', fontSize: 12 },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      force: {
        repulsion: 350,
        edgeLength: [80, 200],
        layoutAnimation: true,
        friction: 0.1,
      },
      roam: true,
      draggable: true,
      data: filteredNodes.map(n => ({
        id: n.id,
        name: n.name,
        value: n.type,
        itemStyle: { color: getColor(n.type) },
        symbolSize: Math.max(20, Math.min(50, 10 + (n.degree || 0) * 3)),
        label: {
          show: props.showLabels,
          color: '#F4F4F4',
          fontSize: 11,
          fontWeight: 500,
          textShadowBlur: 4,
          textShadowColor: '#000',
        },
        description: n.description,
        degree: n.degree,
      })),
      links: filteredEdges.map(e => ({
        source: e.source,
        target: e.target,
        label: {
          show: props.showLabels,
          formatter: e.relationship_name,
          color: '#94A3B8',
          fontSize: 9,
        },
        lineStyle: {
          color: '#333',
          width: 1.5,
          opacity: 0.6,
          curveness: 0.2,
        },
      })),
      edgeLabel: {
        show: props.showLabels,
        fontSize: 9,
        color: '#94A3B8',
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3, opacity: 0.8, color: '#666' },
      },
      blur: {
        opacity: 0.15,
        lineStyle: { opacity: 0.1 },
      },
      lineStyle: { color: 'source' },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1,
        shadowBlur: 6,
        shadowColor: 'rgba(0,0,0,0.3)',
      },
    }],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart.value = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  chart.value.setOption(buildOption())

  chart.value.on('click', (params: any) => {
    if (params.dataType === 'node') {
      const node = props.data.nodes.find(n => n.id === params.data.id)
      if (node) emit('nodeClick', node)
    }
  })
}

function handleResize() {
  chart.value?.resize()
}

watch(
  () => [props.data, props.showLabels, props.activeTypes],
  () => { chart.value?.setOption(buildOption(), true) },
  { deep: true }
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart.value?.dispose()
})

defineExpose({
  zoomIn: () => { /* via ECharts action */ },
  zoomOut: () => { /* via ECharts action */ },
  resetView: () => { chart.value?.setOption(buildOption(), true) },
})
</script>

<style scoped>
.kg-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}
</style>
```

---

### Task 5：详情面板 (GraphDetailPanel.vue)

**Files:**
- Create: `frontend/src/components/GraphDetailPanel.vue`

- [ ] **Step 1: Create GraphDetailPanel.vue**

```vue
<template>
  <transition name="slide">
    <div v-if="node" class="detail-panel">
      <div class="panel-header">
        <h3>{{ node.name }}</h3>
        <el-tag :color="typeColor" effect="dark" size="small">{{ node.type }}</el-tag>
        <el-button class="close-btn" :icon="Close" text @click="$emit('close')" />
      </div>
      <div class="panel-body">
        <p class="description">{{ node.description || '暂无描述' }}</p>

        <div class="section">
          <h4>关系</h4>
          <div v-if="relations.length" class="relation-list">
            <div v-for="rel in relations" :key="`${rel.source}-${rel.target}-${rel.name}`"
                 class="relation-item">
              <span class="rel-direction">{{ rel.direction }}</span>
              <span class="rel-node">{{ rel.targetName }}</span>
              <span class="rel-name">{{ rel.name }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无关联关系" :image-size="40" />
        </div>

        <div class="section">
          <h4>属性</h4>
          <div class="attr-list">
            <div class="attr-item">
              <span class="attr-key">Degree</span>
              <span class="attr-value">{{ node.degree }}</span>
            </div>
            <div class="attr-item">
              <span class="attr-key">ID</span>
              <span class="attr-value">{{ node.id }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import type { GraphNode, GraphEdge } from '@/api/knowledge'
import { useKnowledgeStore } from '@/stores/knowledge'

const props = defineProps<{
  node: GraphNode
}>()

defineEmits<{ close: [] }>()

const store = useKnowledgeStore()

const TYPE_COLORS: Record<string, string> = {
  Concept: '#7C3AED', Algorithm: '#F59E0B', DataStructure: '#10B981',
  Protocol: '#3B82F6', Principle: '#EC4899', Term: '#94A3B8',
  Technology: '#06B6D4', Model: '#F97316',
}

const typeColor = computed(() => TYPE_COLORS[props.node.type] || '#94A3B8')

const relations = computed(() => {
  const edges = store.graphData?.edges ?? []
  return edges
    .filter(e => e.source === props.node.id || e.target === props.node.id)
    .map(e => {
      const isOutgoing = e.source === props.node.id
      const otherId = isOutgoing ? e.target : e.source
      const otherNode = store.graphData?.nodes.find(n => n.id === otherId)
      return {
        source: e.source,
        target: e.target,
        name: e.relationship_name,
        direction: isOutgoing ? '→' : '←',
        targetName: otherNode?.name || otherId,
      }
    })
    .slice(0, 20)
})
</script>

<style scoped>
.detail-panel {
  position: absolute;
  right: 16px;
  top: 16px;
  width: 320px;
  max-height: calc(100vh - 200px);
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 12px;
  overflow-y: auto;
  z-index: 100;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border-bottom: 1px solid #2a2a3e;
}
.panel-header h3 { margin: 0; font-size: 16px; color: #F4F4F4; flex: 1; }
.close-btn { color: #94A3B8; }
.panel-body { padding: 16px; }
.description { font-size: 13px; color: #aaa; line-height: 1.6; margin: 0 0 16px; }
.section { margin-bottom: 16px; }
.section h4 { font-size: 12px; color: #94A3B8; text-transform: uppercase; margin: 0 0 8px; letter-spacing: 0.05em; }
.relation-item { display: flex; align-items: center; gap: 6px; padding: 6px 0; font-size: 13px; }
.rel-direction { color: #3B82F6; font-weight: bold; }
.rel-node { color: #F4F4F4; }
.rel-name { color: #94A3B8; font-size: 11px; margin-left: auto; }
.attr-item { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
.attr-key { color: #94A3B8; }
.attr-value { color: #F4F4F4; }
.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); opacity: 0; }
</style>
```

---

### Task 6：主页面 (KnowledgeExplore.vue)

**Files:**
- Modify: `frontend/src/pages/student/KnowledgeExplore.vue`
- Create: `frontend/src/composables/useGraph.ts`

- [ ] **Step 1: Create composables/useGraph.ts**

```typescript
import { ref } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'

export function useGraph() {
  const store = useKnowledgeStore()
  const showLabels = ref(true)
  const searchResults = ref<Array<{ id: string; name: string; type: string }>>([])

  async function handleSearch(query: string) {
    if (!query.trim()) {
      searchResults.value = []
      return
    }
    const results = await store.searchNodesByQuery(query)
    searchResults.value = results ?? []
  }

  function focusNode(nodeId: string) {
    const node = store.graphData?.nodes.find(n => n.id === nodeId)
    if (node) store.selectNode(node)
  }

  function resetView() {
    store.selectNode(null)
  }

  return {
    showLabels,
    searchResults,
    handleSearch,
    focusNode,
    resetView,
  }
}
```

- [ ] **Step 2: Write KnowledgeExplore.vue**

```vue
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
          <el-button type="primary" @click="store.loadGraphData()">重试</el-button>
        </template>
      </el-result>
    </div>

    <!-- 空状态 -->
    <div v-else-if="store.isEmpty" class="kg-state">
      <el-empty description="还没有构建知识图谱">
        <template #image>
          <div class="empty-graph-icon">🔍</div>
        </template>
        <el-button type="primary" @click="$router.push('/student/ocr')">
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
import { ref, onMounted } from 'vue'
import { Search, ZoomIn, ZoomOut, Refresh } from '@element-plus/icons-vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import GraphDetailPanel from '@/components/GraphDetailPanel.vue'
import { useGraph } from '@/composables/useGraph'

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

onMounted(() => {
  store.loadGraphData()
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
```

---

### Task 7：ECharts 5 的类型声明（如需要）

**Files:**
- Modify: `frontend/tsconfig.json` 或 `frontend/src/env.d.ts`

如果使用 ECharts 5 但项目没有类型声明，需要添加：

```typescript
// frontend/src/env.d.ts (追加)
declare module 'echarts' {
  import { EChartsOption } from 'echarts'
  // 已有声明，仅确认存在
}
```

实际使用时，import 方式为 `import * as echarts from 'echarts'`，ECharts 5 自带类型声明。

- [ ] **Step 1: Verify TypeScript compilation**

```bash
cd G:/dev/chuma/frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: no type errors in the new files.

---

### Task 8：集成验证

- [ ] **Step 1: Verify backend API endpoints**

```bash
# 启动后端
cd G:/dev/chuma/ai && python -c "
from app.kg_pipeline.queries import get_full_graph, search_nodes
# 不实际连接数据库，只验证模块加载和函数签名
import inspect
sig = inspect.signature(get_full_graph)
print(f'get_full_graph{list(sig.parameters.keys())}')  # ['dataset_id']
sig2 = inspect.signature(search_nodes)
print(f'search_nodes{list(sig2.parameters.keys())}')   # ['query', 'dataset_id']
print('API signatures OK')
"
```

- [ ] **Step 2: Verify frontend components**

```bash
cd G:/dev/chuma/frontend && npx vue-tsc --noEmit 2>&1 | grep -i "error" | head -5
```

Expected: no TypeScript errors.

- [ ] **Step 3: Verify the full page renders**

```bash
cd G:/dev/chuma/frontend
npm run build 2>&1 | tail -10
```

Expected: Build succeeds with no errors.
