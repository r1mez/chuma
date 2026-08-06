<template>
  <div ref="chartRef" class="kg-chart-2d" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode } from '@/api/knowledge'

interface ChartNodePayload {
  id: string
  name: string
  value: number
  symbolSize: number
  itemStyle: Record<string, unknown>
  label: Record<string, unknown>
  labelLayout: Record<string, unknown>
  rawNode: GraphNode
}

const props = defineProps<{
  data: GraphData
  showLabels: boolean
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
}>()

const chartRef = ref<HTMLElement>()
const chartInstance = shallowRef<echarts.ECharts>()

function buildChartNode(node: GraphNode): ChartNodePayload {
  const mastery = Math.max(0, Math.min(1, node.mastery || 0))
  const symbolSize = Math.max(30, Math.min(70, 20 + (node.degree || 0) * 3))
  const percentText = `${Math.round(mastery * 100)}%`
  const nameGap = 4
  const nameLineHeight = 15
  const percentLineHeight = Math.round(symbolSize)

  return {
    id: node.id,
    name: node.name,
    value: node.degree || 1,
    symbolSize,
    itemStyle: {
      color: '#6366F1',
      borderColor: '#fff',
      borderWidth: 2,
      shadowBlur: 10,
      shadowColor: 'rgba(99, 102, 241, 0.5)',
    },
    label: {
      show: true,
      position: 'inside',
      offset: props.showLabels ? [0, Math.round((nameGap + nameLineHeight) / 2)] : [0, 0],
      formatter: props.showLabels
        ? `{pct|${percentText}}\n{name|${node.name}}`
        : `{pct|${percentText}}`,
      rich: {
        pct: {
          color: '#fff',
          fontSize: Math.max(14, Math.min(24, Math.round(symbolSize * 0.34))),
          fontWeight: 700,
          align: 'center',
          lineHeight: percentLineHeight,
          textShadowBlur: 8,
          textShadowColor: 'rgba(15, 23, 42, 0.35)',
        },
        name: {
          color: '#334155',
          fontSize: 11,
          fontWeight: 500,
          align: 'center',
          width: Math.max(88, Math.round(symbolSize * 2.4)),
          overflow: 'break',
          lineHeight: nameLineHeight,
          padding: [nameGap, 0, 0, 0],
          textShadowBlur: 2,
          textShadowColor: 'rgba(255, 255, 255, 0.92)',
        },
      },
    },
    labelLayout: {
      hideOverlap: false,
    },
    rawNode: node,
  }
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
  if (!chartInstance.value || !props.data) return

  const nodes = props.data.nodes.map(buildChartNode)
  const links = props.data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    lineStyle: {
      width: 2,
      color: '#94A3B8',
      opacity: 0.6,
    },
  }))

  chartInstance.value.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => (params.dataType === 'node' ? params.data.name : ''),
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        nodes,
        links,
        roam: true,
        force: {
          repulsion: 800,
          edgeLength: 200,
          gravity: 0.1,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 },
        },
      },
    ],
  })
}

function handleResize() {
  chartInstance.value?.resize()
}

watch(
  () => [props.data, props.showLabels],
  () => {
    updateChart()
  },
  { deep: true },
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  window.removeEventListener('resize', handleResize)
})

defineExpose({
  zoomIn: () => {
    if (!chartInstance.value) return
    const option = chartInstance.value.getOption() as any
    if (option?.series?.[0]) {
      const currentZoom = option.series[0].zoom || 1
      chartInstance.value.setOption({ series: [{ zoom: currentZoom * 1.2 }] })
    }
  },
  zoomOut: () => {
    if (!chartInstance.value) return
    const option = chartInstance.value.getOption() as any
    if (option?.series?.[0]) {
      const currentZoom = option.series[0].zoom || 1
      chartInstance.value.setOption({ series: [{ zoom: currentZoom / 1.2 }] })
    }
  },
  resetView: () => {
    if (!chartInstance.value) return
    chartInstance.value.setOption({ series: [{ zoom: 1, center: null }] })
  },
})
</script>

<style scoped>
.kg-chart-2d {
  width: 100%;
  height: 100%;
  min-height: 500px;
  background: transparent;
}
</style>
