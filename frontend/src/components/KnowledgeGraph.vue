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
  expandedNodeIds: Set<string>
  anchorNodeIds?: Set<string>
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
  nodeDblClick: [node: GraphNode]
}>()

const store = useKnowledgeStore()
const chartRef = ref<HTMLElement>()
const chart = shallowRef<echarts.ECharts>()
let clickTimer: ReturnType<typeof setTimeout> | null = null

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
        itemStyle: {
          color: getColor(n.type),
          borderColor: props.anchorNodeIds?.has(n.id)
            ? '#00E5FF'
            : props.expandedNodeIds.has(n.id)
              ? '#FFD700'
              : '#fff',
          borderWidth: props.anchorNodeIds?.has(n.id)
            ? 4
            : props.expandedNodeIds.has(n.id)
              ? 3
              : 1,
          shadowBlur: props.anchorNodeIds?.has(n.id)
            ? 24
            : props.expandedNodeIds.has(n.id)
              ? 16
              : 6,
          shadowColor: props.anchorNodeIds?.has(n.id)
            ? 'rgba(0, 229, 255, 0.8)'
            : props.expandedNodeIds.has(n.id)
              ? 'rgba(255, 215, 0, 0.6)'
              : 'rgba(0,0,0,0.3)',
        },
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
    }],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart.value = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  chart.value.setOption(buildOption())

  chart.value.on('click', (params: any) => {
    if (params.dataType === 'node') {
      // 延迟执行单击，若 300ms 内发生双击则取消
      clickTimer = setTimeout(() => {
        const node = props.data.nodes.find(n => n.id === params.data.id)
        if (node) emit('nodeClick', node)
      }, 300)
    }
  })

  chart.value.on('dblclick', (params: any) => {
    if (clickTimer) {
      clearTimeout(clickTimer)
      clickTimer = null
    }
    if (params.dataType === 'node') {
      const node = props.data.nodes.find(n => n.id === params.data.id)
      if (node && node.type !== 'Chapter') {
        emit('nodeDblClick', node)
      }
    }
  })
}

function handleResize() {
  chart.value?.resize()
}

watch(
  () => [props.data, props.showLabels, props.activeTypes, props.expandedNodeIds],
  () => { chart.value?.setOption(buildOption(), true) },
  { deep: true }
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (clickTimer) clearTimeout(clickTimer)
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
