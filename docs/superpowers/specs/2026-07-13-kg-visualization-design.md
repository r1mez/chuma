# 知识图谱可视化设计文档

> 日期：2026-07-13
> 状态：已批准

## 1. 概述

在现有项目中新增知识图谱可视化功能，参照 Cognee 的暗色主题力导向图风格，在 Vue 3 前端通过 ECharts 实现交互式图可视化。

### 1.1 核心流程

```
AGE 图数据库
  → 后端 API (GET /kg/graph/data)
  → 前端 API 调用层 (api/knowledge.ts)
  → Pinia Store (stores/knowledge.ts)
  → ECharts Force Graph 渲染
  → 用户交互（平移/缩放/点击/搜索）
```

## 2. 后端 API

### 2.1 GET /kg/graph/data

从 AGE 读取全量节点和边，返回 ECharts graph 系列兼容的 JSON。

```python
@router.get("/graph/data")
async def get_graph_data(dataset_id: str = "main"):
    """获取知识图谱全量数据"""
    nodes, edges, stats = await kg_queries.get_full_graph(dataset_id)
    return {"nodes": nodes, "edges": edges, "stats": stats}
```

**响应格式：**

```json
{
  "nodes": [
    {"id": "TCP", "name": "TCP", "type": "Protocol",
     "description": "传输控制协议", "degree": 5}
  ],
  "edges": [
    {"source": "TCP", "target": "IP",
     "relationship_name": "depends_on",
     "description": "TCP 依赖 IP 协议传输数据"}
  ],
  "stats": {
    "total_nodes": 42, "total_edges": 67,
    "node_types": {"Concept": 15, "Protocol": 8, ...}
  }
}
```

### 2.2 GET /kg/graph/search

```python
@router.get("/graph/search")
async def search_nodes(q: str, dataset_id: str = "main"):
    """按名称搜索实体"""
```

### 2.3 AST_RELATIONS (可选，后续迭代)

支持查询单个节点的邻接子图（减少前端渲染压力）。

## 3. 前端 API 层

`frontend/src/api/knowledge.ts`:

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

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    total_nodes: number
    total_edges: number
    node_types: Record<string, number>
  }
}

export async function fetchGraphData(datasetId = 'main'): Promise<GraphData> {
  return request.get('/kg/graph/data', { params: { dataset_id: datasetId } })
}

export async function searchNodes(query: string, datasetId = 'main') {
  return request.get('/kg/graph/search', { params: { q: query, dataset_id: datasetId } })
}
```

## 4. Pinia Store

`frontend/src/stores/knowledge.ts`:

```typescript
export const useKnowledgeStore = defineStore('knowledge', () => {
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<GraphError | null>(null)
  const selectedNode = ref<GraphNode | null>(null)
  const searchQuery = ref('')

  async function loadGraphData(datasetId = 'main') { ... }
  async function searchNodes(query: string) { ... }

  return { graphData, loading, error, selectedNode, searchQuery,
           loadGraphData, searchNodes }
})
```

## 5. 可视化组件

### 5.1 KnowledgeGraph.vue

ECharts 力导向图核心组件，参照 Cognee 风格：

| 特性 | 实现 |
|------|------|
| 布局 | `type: 'graph', layout: 'force'` |
| 颜色 | 按 EntityType 映射固定色板 |
| 节点大小 | `symbolSize` = degree 映射 |
| 悬停 | `emphasis.focus: 'adjacency'` |
| 缩放/平移 | `roam: true` |
| 边标签 | `edgeLabel` 显示 relationship_name |
| 背景 | `#0F0F0F` 暗色 |

### 5.2 颜色映射 (Cognee 风格)

| EntityType | Color | 色值 |
|-----------|-------|------|
| Concept | 紫色 | `#7C3AED` |
| Algorithm | 琥珀色 | `#F59E0B` |
| DataStructure | 翠绿 | `#10B981` |
| Protocol | 蓝色 | `#3B82F6` |
| Principle | 粉色 | `#EC4899` |
| Term | 灰色 | `#94A3B8` |
| Technology | 青色 | `#06B6D4` |
| Model | 橙色 | `#F97316` |

### 5.3 GraphDetailPanel.vue

点击节点后滑出的详情面板：

```
┌──────────────────────┐
│ TCP                ✕ │
│ Protocol             │
│                      │
│ 传输控制协议（TCP）是   │
│ 面向连接的、可靠的、    │
│ 基于字节流的传输层      │
│ 通信协议。            │
│                      │
│ ─── 关系 ───          │
│ → IP      depends_on │
│ ← UDP    contrasts   │
│ → HTTP   supports    │
│                      │
│ ─── 属性 ───          │
│ degree: 5            │
│ source: 第3章 切片1   │
└──────────────────────┘
```

## 6. 页面状态

| 状态 | 展示 |
|------|------|
| Loading | 骨架屏 + "正在加载知识图谱..." |
| Empty | 空状态引导 → "上传文档构建" 按钮 |
| Error | 错误类型区分 + 重试按钮 |
| Success | ECharts 图 + 工具栏 + 图例 |

## 7. 交互行为

| 交互 | 行为 |
|------|------|
| 悬停节点 | 高亮自身 + 邻接边/节点 |
| 点击节点 | 打开详情面板 |
| 搜索 | 实时过滤高亮匹配节点 |
| 图例点击 | 切换显示某类型节点 |
| 滚轮 | 缩放 |
| 拖拽空白 | 平移 |
| 拖拽节点 | 调整布局 |

## 8. 颜色与主题

- 背景：`#0F0F0F`（近似 Cognee 的黑色）
- 文本：`#F4F4F4`（浅灰白）
- 次要文本：`#94A3B8`（灰蓝）
- 边颜色：`#333333`，透明度 0.6

## 9. 文件清单

| 路径 | 操作 | 说明 |
|------|------|------|
| `ai/app/api/kg.py` | 修改 | 新增 GET /graph/data, /graph/search |
| `ai/app/kg_pipeline/queries.py` | 新建 | AGE 查询封装：`get_full_graph()`, `search_nodes()` — 通过现有 AgeStorage 连接执行 Cypher 读取 |
| `frontend/src/api/knowledge.ts` | 修改 | 新增 fetchGraphData, searchNodes |
| `frontend/src/stores/knowledge.ts` | 修改 | 扩展完整的图状态管理 |
| `frontend/src/pages/student/KnowledgeExplore.vue` | 修改 | 完整实现图页面 |
| `frontend/src/components/KnowledgeGraph.vue` | 新建 | ECharts 力导向图组件 |
| `frontend/src/components/GraphDetailPanel.vue` | 新建 | 节点详情面板 |
| `frontend/src/composables/useGraph.ts` | 新建 | 图交互逻辑组合式函数 |

## 10. 未来扩展

- **子图展开**：点击节点时动态加载其 N 度邻居（避免全量加载大图）
- **导出功能**：将当前图导出为图片（ECharts 原生支持）
- **节点笔记**：在图谱节点上添加学习笔记
- **路径查找**：可视化两个节点之间的连接路径
