<template>
  <div ref="chartRef" class="kg-chart-2d" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode } from '@/api/knowledge'

const props = defineProps<{
  data: GraphData
  showLabels: boolean
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
}>()

const chartRef = ref<HTMLElement>()
const chartInstance = shallowRef<echarts.ECharts>()

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

  const nodes = props.data.nodes.map(n => ({
    id: n.id,
    name: n.name,
    value: n.degree || 1,
    symbolSize: Math.max(30, Math.min(70, 20 + (n.degree || 0) * 3)),
    itemStyle: { 
      color: '#6366F1', // 章节节点统一颜色
      borderColor: '#fff',
      borderWidth: 2,
      shadowBlur: 10,
      shadowColor: 'rgba(99, 102, 241, 0.5)'
    },
    label: { 
      show: props.showLabels, 
      position: 'bottom', 
      color: '#333',
      fontSize: 14,
      fontWeight: 'bold'
    },
    rawNode: n
  }))

  const links = props.data.edges.map(e => ({
    source: e.source,
    target: e.target,
    lineStyle: { width: 2, color: '#94A3B8', opacity: 0.6 }
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'item',
      formatter: (params: any) => params.dataType === 'node' ? params.data.name : ''
    },
    series: [{
      type: 'graph',
      layout: 'force',
      nodes,
      links,
      roam: true,
      label: { show: props.showLabels, position: 'bottom' },
      force: { 
        repulsion: 800, 
        edgeLength: 200,
        gravity: 0.1
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 4 }
      }
    }]
  }
  
  chartInstance.value.setOption(option)
}

watch(() => [props.data, props.showLabels], () => {
  updateChart()
}, { deep: true })

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

function handleResize() {
  chartInstance.value?.resize()
}

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
  }
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
