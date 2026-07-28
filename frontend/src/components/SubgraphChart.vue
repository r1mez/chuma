<template>
  <div ref="chartRef" class="subgraph-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as echarts from 'echarts'
import type { GraphNode, GraphEdge } from '@/api/knowledge'
import { TYPE_COLORS, HIT_NODE_COLOR } from '@/constants/knowledgeColors'

const props = defineProps<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  hitNodeId: string
  direction: 'upstream' | 'downstream'
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
}>()

const chartRef = ref<HTMLElement>()
const chartInstance = shallowRef<echarts.ECharts>()
let resizeObserver: ResizeObserver | null = null

function getHopLevel(nodeId: string): number {
  if (nodeId === props.hitNodeId) return 0

  const isUpstream = props.direction === 'upstream'
  for (const edge of props.edges) {
    if (isUpstream && edge.target === props.hitNodeId && edge.source === nodeId) return 1
    if (!isUpstream && edge.source === props.hitNodeId && edge.target === nodeId) return 1
  }

  const oneHopIds = new Set<string>()
  for (const edge of props.edges) {
    if (isUpstream && edge.target === props.hitNodeId) oneHopIds.add(edge.source)
    if (!isUpstream && edge.source === props.hitNodeId) oneHopIds.add(edge.target)
  }
  for (const edge of props.edges) {
    if (isUpstream && oneHopIds.has(edge.target) && edge.source === nodeId) return 2
    if (!isUpstream && oneHopIds.has(edge.source) && edge.target === nodeId) return 2
  }

  return 2
}

function initChart() {
  if (!chartRef.value) return
  chartInstance.value = echarts.init(chartRef.value)

  chartInstance.value.on('click', (params: any) => {
    if (params.dataType === 'node' && params.data.rawNode) {
      emit('nodeClick', params.data.rawNode)
    }
  })

  updateChart()
}

function updateChart() {
  if (!chartInstance.value) return
  if (!props.nodes.length && !props.edges.length) return

  const allNodeIds = new Set([props.hitNodeId, ...props.nodes.map(n => n.id)])
  const relevantEdges = props.edges.filter(e => allNodeIds.has(e.source) && allNodeIds.has(e.target))

  const allNodes: GraphNode[] = []
  const nodeById = new Map(props.nodes.map(n => [n.id, n]))

  if (!nodeById.has(props.hitNodeId)) {
    allNodes.push({
      id: props.hitNodeId,
      name: props.hitNodeId,
      type: 'Concept',
      description: '',
      degree: 0,
    })
  }
  for (const n of props.nodes) {
    if (!allNodeIds.has(n.id)) continue
    allNodes.push(n)
  }

  const echartsNodes = allNodes.map(n => {
    const hop = getHopLevel(n.id)
    let symbolSize: number
    let color: string
    let opacity: number

    if (hop === 0) {
      symbolSize = 40
      color = HIT_NODE_COLOR
      opacity = 1
    } else if (hop === 1) {
      symbolSize = 28
      color = TYPE_COLORS[n.type] || '#94A3B8'
      opacity = 1
    } else {
      symbolSize = 18
      color = TYPE_COLORS[n.type] || '#94A3B8'
      opacity = 0.6
    }

    return {
      id: n.id,
      name: n.name,
      symbolSize,
      itemStyle: {
        color,
        borderColor: hop === 0 ? '#fff' : 'transparent',
        borderWidth: hop === 0 ? 3 : 0,
        opacity,
        shadowBlur: hop === 0 ? 12 : 0,
        shadowColor: hop === 0 ? 'rgba(255, 140, 0, 0.6)' : 'transparent',
      },
      label: {
        show: true,
        position: 'bottom' as const,
        color: hop === 0 ? HIT_NODE_COLOR : '#666',
        fontSize: hop === 0 ? 13 : hop === 1 ? 11 : 9,
        fontWeight: hop === 0 ? 'bold' : 'normal',
      },
      rawNode: n,
    }
  })

  const echartsLinks = relevantEdges.map(e => ({
    source: e.source,
    target: e.target,
    lineStyle: {
      width: 1.5,
      color: '#94A3B8',
      opacity: 0.5,
      curveness: 0.1,
    },
    symbol: ['none', 'arrow'],
    symbolSize: 8,
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const node = params.data.rawNode
          return `${node.name} (${node.type})`
        }
        return ''
      },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      nodes: echartsNodes,
      links: echartsLinks,
      roam: false,
      force: {
        repulsion: 300,
        edgeLength: 100,
        gravity: 0.15,
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3 },
      },
    }],
  }

  chartInstance.value.setOption(option, true)
}

watch(() => [props.nodes, props.edges, props.hitNodeId, props.direction], () => {
  updateChart()
}, { deep: true })

onMounted(() => {
  initChart()
  // Observe container resize (especially for panel slide transition)
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chartInstance.value?.resize()
    })
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
})
</script>

<style scoped>
.subgraph-chart {
  width: 100%;
  height: 100%;
  min-height: 180px;
  background: transparent;
}
</style>
