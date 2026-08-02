<template>
  <div ref="containerRef" class="kg-editor-canvas" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef, nextTick } from 'vue'
import { Graph } from '@antv/g6'
import type { GraphData as AppGraphData, GraphNode, GraphEdge } from '@/api/knowledge'
import { TYPE_COLORS } from '@/constants/knowledgeColors'

const props = defineProps<{
  data: AppGraphData | null
  toolMode: 'select' | 'add-node' | 'add-edge'
  visibleTypes: Set<string>
}>()

const emit = defineEmits<{
  'node-selected': [nodeData: NodeEditData | null]
  'edge-selected': [edgeData: EdgeEditData | null]
  'canvas-click': [coords: { x: number; y: number }]
  'edge-created': [edge: any]
}>()

const containerRef = ref<HTMLElement>()
const graphInstance = shallowRef<Graph>()

// ---- Exported data types for panel consumption ----

export interface NodeEditData {
  id: string
  name: string
  type: string
  description: string
}

export interface EdgeEditData {
  id: string
  source: string
  target: string
  sourceName: string
  targetName: string
  relationship_name: string
  description: string
}

// ---- Data format conversion ----

function toG6Nodes(nodes: GraphNode[]) {
  return nodes.map(n => ({
    id: n.id,
    data: {
      label: n.name,
      type: n.type,
      description: n.description,
    },
    style: {
      fill: TYPE_COLORS[n.type] || '#94A3B8',
      stroke: '#fff',
      lineWidth: 2,
      size: Math.max(30, Math.min(60, 20 + (n.degree || 0) * 2)),
    },
  }))
}

function toG6Edges(edges: GraphEdge[]) {
  return edges.map(e => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    data: {
      label: e.relationship_name,
      description: e.description || '',
    },
  }))
}

// ---- G6 initialization ----

function initGraph() {
  if (!containerRef.value) return

  const graph = new Graph({
    container: containerRef.value,
    autoFit: 'view',
    node: {
      style: {
        size: (d: any) => d.style?.size || 40,
        fill: (d: any) => d.style?.fill || '#94A3B8',
        stroke: (d: any) => d.style?.stroke || '#fff',
        lineWidth: (d: any) => d.style?.lineWidth || 2,
        labelText: (d: any) => d.data?.label || '',
        labelFontSize: 12,
        labelPlacement: 'bottom',
        labelOffsetY: 4,
      },
      state: {
        selected: {
          stroke: '#E6A23C',
          lineWidth: 4,
          shadowColor: 'rgba(230, 162, 60, 0.5)',
          shadowBlur: 10,
        },
        hover: {
          stroke: '#E6A23C',
          lineWidth: 3,
        },
        dim: {
          opacity: 0.25,
        },
      },
    },
    edge: {
      type: 'line',
      style: {
        stroke: '#94A3B8',
        lineWidth: 1.5,
        endArrow: true,
        labelText: (d: any) => d.data?.label || '',
        labelFontSize: 10,
        labelFill: '#6b7280',
        labelBackground: true,
        labelBackgroundFill: '#fff',
        labelBackgroundOpacity: 0.8,
        labelBackgroundRadius: 2,
        labelPadding: [2, 4],
      },
      state: {
        selected: {
          stroke: '#E6A23C',
          lineWidth: 3,
        },
        hover: {
          stroke: '#E6A23C',
          lineWidth: 2,
        },
        dim: {
          opacity: 0.15,
        },
      },
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeStrength: -300,
      edgeStrength: 0.1,
      linkDistance: 180,
    },
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      'drag-element',
      {
        type: 'click-select',
        multiple: false,
        trigger: 'click',
      },
    ],
    plugins: [],
    animation: false,
  })

  // Node click
  graph.on('node:click', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    const nodeData = graph.getNodeData(nodeId)
    if (nodeData) {
      dimUnselected(nodeId, 'node')
      const d = nodeData.data as Record<string, unknown> | undefined
      emit('node-selected', {
        id: nodeId,
        name: (d?.label as string) || '',
        type: (d?.type as string) || '',
        description: (d?.description as string) || '',
      })
    }
  })

  // Edge click
  graph.on('edge:click', (evt: any) => {
    const edgeId = evt.target?.id
    if (!edgeId) return
    const edgeData = graph.getEdgeData(edgeId)
    if (edgeData) {
      dimUnselected(edgeId, 'edge')
      const d = edgeData.data as Record<string, unknown> | undefined
      const srcNode = graph.getNodeData(edgeData.source)
      const tgtNode = graph.getNodeData(edgeData.target)
      const srcD = srcNode?.data as Record<string, unknown> | undefined
      const tgtD = tgtNode?.data as Record<string, unknown> | undefined
      emit('edge-selected', {
        id: edgeId,
        source: edgeData.source,
        target: edgeData.target,
        sourceName: (srcD?.label as string) || edgeData.source,
        targetName: (tgtD?.label as string) || edgeData.target,
        relationship_name: (d?.label as string) || '',
        description: (d?.description as string) || '',
      })
    }
  })

  // Canvas blank click — emit canvas coordinates so parent can addTempNode(x, y, id)
  graph.on('canvas:click', (evt: any) => {
    resetHighlight()
    const clientX = evt.client?.x
    const clientY = evt.client?.y
    if (clientX != null && clientY != null) {
      const [cx, cy] = graph.getCanvasByClient([clientX, clientY])
      emit('canvas-click', { x: cx, y: cy })
    } else {
      emit('canvas-click', { x: 0, y: 0 })
    }
  })

  graphInstance.value = graph
}

// ---- Highlight / dim ----

function dimUnselected(selectedId: string, _type: 'node' | 'edge') {
  const graph = graphInstance.value
  if (!graph) return

  const allNodes = graph.getNodeData()
  const allEdges = graph.getEdgeData()

  allNodes.forEach((n) => {
    if (n.id !== selectedId) {
      graph.setElementState(n.id, ['dim'])
    } else {
      graph.setElementState(n.id, ['selected'])
    }
  })

  allEdges.forEach((e) => {
    if (!e.id) return
    if (e.id !== selectedId) {
      graph.setElementState(e.id, ['dim'])
    } else {
      graph.setElementState(e.id, ['selected'])
    }
  })
}

function resetHighlight() {
  const graph = graphInstance.value
  if (!graph) return
  const allNodes = graph.getNodeData()
  const allEdges = graph.getEdgeData()
  allNodes.forEach((n) => graph.setElementState(n.id, []))
  allEdges.forEach((e) => { if (e.id) graph.setElementState(e.id, []) })
}

// ---- Data rendering ----

function renderData(data: AppGraphData) {
  const graph = graphInstance.value
  if (!graph) return

  const nodes = toG6Nodes(data.nodes)
  const edges = toG6Edges(data.edges)

  graph.setData({ nodes, edges })
  graph.render()
}

// ---- Type filter ----

function applyTypeFilter(visibleTypes: Set<string>) {
  const graph = graphInstance.value
  if (!graph) return

  const allNodes = graph.getNodeData()
  const hiddenNodeIds = new Set<string>()

  allNodes.forEach((n) => {
    const d = n.data as Record<string, unknown> | undefined
    const nodeType = (d?.type as string) || ''
    if (visibleTypes.has(nodeType)) {
      graph.showElement(n.id)
    } else {
      graph.hideElement(n.id)
      hiddenNodeIds.add(n.id)
    }
  })

  // Edge visibility depends on both endpoint nodes
  const allEdges = graph.getEdgeData()
  allEdges.forEach((e) => {
    if (!e.id) return
    if (hiddenNodeIds.has(e.source) || hiddenNodeIds.has(e.target)) {
      graph.hideElement(e.id)
    } else {
      graph.showElement(e.id)
    }
  })
}

// ---- Watchers ----

watch(() => props.data, (newData) => {
  if (newData) {
    nextTick(() => renderData(newData))
  }
}, { deep: false })

watch(() => props.visibleTypes, (newTypes) => {
  applyTypeFilter(newTypes)
}, { deep: true })

watch(() => props.toolMode, (newMode) => {
  const graph = graphInstance.value
  if (!graph) return

  // Toggle create-edge behavior via setBehaviors functional update
  if (newMode === 'add-edge') {
    graph.setBehaviors((prev) => {
      // Guard against duplicate create-edge behavior
      const alreadyHas = prev.some((b: any) =>
        b.type === 'create-edge' || b === 'create-edge' || b.key === 'create-edge',
      )
      if (alreadyHas) return prev
      return [...prev, {
        type: 'create-edge',
        key: 'create-edge',
        trigger: 'click',
        onFinish: (edge: any) => { emit('edge-created', edge) },
      }]
    })
  } else {
    graph.setBehaviors((prev) =>
      prev.filter((b: any) => b.type !== 'create-edge' && b !== 'create-edge' && b.key !== 'create-edge'),
    )
  }

  // Update cursor style
  if (containerRef.value) {
    containerRef.value.style.cursor = newMode === 'select' ? 'default' : 'crosshair'
  }
})

// ---- Lifecycle ----

onMounted(() => {
  initGraph()
  if (props.data) {
    nextTick(() => renderData(props.data!))
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (graphInstance.value) {
    graphInstance.value.destroy()
  }
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  graphInstance.value?.resize()
}

// ---- Expose methods for parent component ----

defineExpose({
  /** Zoom in by 1.2x */
  zoomIn: () => graphInstance.value?.zoomBy(1.2),
  /** Zoom out by 0.8x */
  zoomOut: () => graphInstance.value?.zoomBy(0.8),
  /** Fit the graph to the viewport */
  fitView: () => graphInstance.value?.fitView(),

  /** Add a temporary node at the given canvas position */
  addTempNode: (x: number, y: number, tempId: string): void => {
    const graph = graphInstance.value
    if (!graph) return
    graph.addNodeData([{
      id: tempId,
      data: { label: '新节点', type: 'Concept', description: '' },
      style: { fill: '#94A3B8', stroke: '#E6A23C', lineWidth: 3, size: 40 },
    }])
    // Move the node to the click position
    graph.translateElementTo(tempId, [x, y])
  },

  /** Remove a node or edge by ID */
  removeItemById: (id: string, type: 'node' | 'edge'): void => {
    const graph = graphInstance.value
    if (!graph) return
    if (type === 'node') {
      graph.removeNodeData([id])
    } else {
      graph.removeEdgeData([id])
    }
  },

  /** Update node data (optimistic update) */
  updateNodeData: (nodeId: string, fields: Partial<NodeEditData>): void => {
    const graph = graphInstance.value
    if (!graph) return
    const existing = graph.getNodeData(nodeId)
    if (!existing) return
    const prevData = existing.data as Record<string, unknown> | undefined
    const prevStyle = existing.style as Record<string, unknown> | undefined
    const newType = fields.type ?? (prevData?.type as string | undefined)
    graph.updateNodeData([{
      id: nodeId,
      data: {
        ...prevData,
        label: fields.name ?? prevData?.label,
        type: newType,
        description: fields.description ?? prevData?.description,
      },
      style: {
        ...prevStyle,
        fill: (newType ? TYPE_COLORS[newType] : prevStyle?.fill) as string,
      },
    }])
  },

  /** Update edge data (optimistic update) */
  updateEdgeData: (edgeId: string, fields: { relationship_name?: string; description?: string }): void => {
    const graph = graphInstance.value
    if (!graph) return
    const existing = graph.getEdgeData(edgeId)
    if (!existing) return
    const prevData = existing.data as Record<string, unknown> | undefined
    graph.updateEdgeData([{
      id: edgeId,
      data: {
        ...prevData,
        label: fields.relationship_name ?? prevData?.label,
        description: fields.description ?? prevData?.description,
      },
    }])
  },

  /** Get all edge IDs connected to a given node */
  getRelatedEdges: (nodeId: string): string[] => {
    const graph = graphInstance.value
    if (!graph) return []
    const edges = graph.getRelatedEdgesData(nodeId)
    return edges.map((e) => e.id).filter((id): id is string => id !== undefined)
  },

  /** Get the raw G6 graph instance (advanced usage) */
  getGraph: () => graphInstance.value,

  /** Reset all highlight/dim states */
  resetHighlight,
})
</script>

<style scoped>
.kg-editor-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: #fafafa;
}
</style>
