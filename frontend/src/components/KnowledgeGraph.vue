<template>
  <div ref="chartRef" class="kg-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode, GraphEdge } from '@/api/knowledge'
import { useKnowledgeStore } from '@/stores/knowledge'

const props = defineProps<{
  data: GraphData
  showLabels: boolean
  activeTypes: Set<string>
  expandedNodeIds: Set<string>
  anchorNodeIds?: Set<string>
  highlightedNodeIds?: Set<string>
  nodeFxMap?: Record<string, {fx?: number; fy?: number}>
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

  // 展开（有 nodeFxMap 数据）时禁用入场动画，让节点直接出现在正确位置
  // 避免 notMerge: true 重建图表时的"全量闪烁"效果
  const hasFxMap = props.nodeFxMap && Object.keys(props.nodeFxMap).length > 0

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
      animation: hasFxMap ? false : undefined,
      animationDuration: hasFxMap ? 0 : 600,
      animationDurationUpdate: hasFxMap ? 0 : 600,
      animationEasingUpdate: 'cubicOut',
      roam: true,
      draggable: true,
      data: filteredNodes.map(n => {
        const layout = props.nodeFxMap?.[n.id]
        const isHighlighted = props.highlightedNodeIds?.has(n.id)
        const isAnchor = props.anchorNodeIds?.has(n.id)
        const isExpanded = props.expandedNodeIds.has(n.id)

        // 调试日志
        if (layout) {
          console.log('节点', n.id, '使用 fx/fy:', layout)
        }

        let borderColor = '#fff'
        let borderWidth = 1
        let shadowBlur = 6
        let shadowColor = 'rgba(0,0,0,0.3)'

        if (isHighlighted) {
          // 橙色高亮（已存在于图中的一跳节点）
          borderColor = '#FF8C00'
          borderWidth = 3
          shadowBlur = 16
          shadowColor = 'rgba(255, 140, 0, 0.6)'
        }
        if (isAnchor) {
          borderColor = '#00E5FF'
          borderWidth = 4
          shadowBlur = 24
          shadowColor = 'rgba(0, 229, 255, 0.8)'
        } else if (isExpanded && !isHighlighted) {
          // 新展开的节点（非橙色）
          borderColor = '#A78BFA'
          borderWidth = 3
          shadowBlur = 16
          shadowColor = 'rgba(167, 139, 250, 0.6)'
        }

        // 高亮节点的填充色也变为橙色
        const fillColor = isHighlighted ? '#FF8C00' : getColor(n.type)

        return {
          id: n.id,
          name: n.name,
          value: n.type,
          x: layout?.fx,  // 初始位置 = 目标固定位置，force 布局从此开始
          y: layout?.fy,
          fx: layout?.fx,
          fy: layout?.fy,
          fixed: layout ? true : undefined,  // 有 fx/fy 的节点需显式标记为固定
          itemStyle: {
            color: fillColor,
            borderColor,
            borderWidth,
            shadowBlur,
            shadowColor,
          },
          symbolSize: isHighlighted
            ? Math.max(22, Math.min(55, 12 + (n.degree || 0) * 3))  // 橙色节点稍微放大
            : Math.max(20, Math.min(50, 10 + (n.degree || 0) * 3)),
          label: {
            show: props.showLabels,
            color: isHighlighted ? '#FF8C00' : '#F4F4F4',
            fontSize: isHighlighted ? 12 : 11,
            fontWeight: isHighlighted ? 600 : 500,
            textShadowBlur: 4,
            textShadowColor: '#000',
          },
          description: n.description,
          degree: n.degree,
        }
      }),
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
  () => [props.data, props.showLabels, props.activeTypes, props.expandedNodeIds, props.highlightedNodeIds, props.nodeFxMap],
  () => {
    console.log('=== ECharts 更新 ===')
    console.log('节点数量:', props.data.nodes.length)
    console.log('边数量:', props.data.edges.length)
    console.log('fxMap 大小:', Object.keys(props.nodeFxMap || {}).length)
    nextTick(() => {
      chart.value?.setOption(buildOption(), { notMerge: true, lazyUpdate: false })
    })
  },
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

function getNodePositions(): Map<string, {x: number; y: number}> {
  const result = new Map<string, {x: number; y: number}>()
  if (!chart.value) return result
  try {
    const seriesModel = (chart.value as any).getModel().getSeries()[0]
    if (!seriesModel) return result
    // ECharts 力导布局将坐标写入 GraphNode.setLayout([x, y])，而非 data.setItemLayout()
    // series.getData().getItemLayout(i) 对 graph series 不返回布局计算结果
    // 正确做法：通过 series.getGraph().nodes 遍历，从 GraphNode.getLayout() 读取
    const graph = (seriesModel as any).getGraph?.()
    if (!graph || !graph.nodes) return result
    for (const node of graph.nodes) {
      if (!node.id) continue
      const layout = node.getLayout?.()
      if (layout && Array.isArray(layout) && layout.length >= 2
          && !isNaN(layout[0]) && !isNaN(layout[1])) {
        result.set(String(node.id), { x: layout[0], y: layout[1] })
      }
    }
  } catch {
    // ECharts 内部状态可能不完整
  }
  return result
}

defineExpose({
  zoomIn: () => { /* via ECharts action */ },
  zoomOut: () => { /* via ECharts action */ },
  resetView: () => { chart.value?.setOption(buildOption(), true) },
  getNodePositions,
})
</script>

<style scoped>
.kg-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}
</style>
