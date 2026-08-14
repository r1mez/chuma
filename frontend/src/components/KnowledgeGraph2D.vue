<template>
  <div class="kg-chart-shell">
    <div ref="chartRef" class="kg-chart-2d" />
    <svg ref="edgeOverlayRef" class="kg-edge-overlay" aria-hidden="true" />
    <div ref="waveOverlayRef" class="kg-wave-overlay" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'
import type { GraphData, GraphNode } from '@/api/knowledge'
import { TYPE_COLORS } from '@/constants/knowledgeColors'

interface ChartNodePayload {
  id: string
  name: string
  value: number
  symbolSize: number
  itemStyle: Record<string, unknown>
  label: Record<string, unknown>
  labelLayout: Record<string, unknown>
  symbol?: string
  rawNode: GraphNode
}

const props = defineProps<{
  data: GraphData
  showLabels: boolean
  activeTypes?: Set<string>
  showMasteryWave?: boolean
  highlightedNodeIds?: Set<string>
  highlightedEdgeIds?: Set<string>
}>()

const emit = defineEmits<{
  nodeClick: [node: GraphNode]
  nodeDblClick: [node: GraphNode]
}>()

const chartRef = ref<HTMLElement>()
const edgeOverlayRef = ref<SVGSVGElement>()
const waveOverlayRef = ref<HTMLElement>()
const chartInstance = shallowRef<echarts.ECharts>()
let clickTimer: ReturnType<typeof setTimeout> | null = null
let waveOverlayFrame: number | null = null
const waveOverlayNodes = new Map<string, HTMLElement>()
const edgeOverlayGroups = new Map<string, SVGGElement>()
let edgeOverlayMode: boolean | null = null
let resizeObserver: ResizeObserver | null = null
const DEPENDENCY_RELATIONS = new Set(['依赖', '前提'])
const RELATION_COLORS: Record<string, string> = {
  使用: '#A78BFA',
  属于: '#F59E0B',
  应用: '#34D399',
  基于: '#F97316',
  实现: '#F472B6',
  组成部分: '#94A3B8',
}

function getRelationColor(edge: { relationship_name: string }): string {
  const relationName = edge.relationship_name.trim()
  if (DEPENDENCY_RELATIONS.has(relationName)) return '#38BDF8'
  return RELATION_COLORS[relationName] || '#94A3B8'
}

function edgeKey(edge: { source: string; target: string; relationship_name: string }): string {
  return `${edge.source}->${edge.target}:${edge.relationship_name}`
}

function buildChartNode(node: GraphNode): ChartNodePayload {
  const mastery = Math.max(0, Math.min(1, node.mastery || 0))
  const symbolSize = Math.max(30, Math.min(70, 20 + (node.degree || 0) * 3))
  const percentText = `${Math.round(mastery * 100)}%`
  const nameGap = 4
  const nameLineHeight = 15
  const percentLineHeight = Math.round(symbolSize)

  const waveMode = props.showMasteryWave && node.type !== 'Chapter'
  const pathMode = props.highlightedNodeIds?.size
  const isPathNode = props.highlightedNodeIds?.has(node.id) ?? false
  const nodeColor = node.type === 'Chapter' ? '#6366F1' : (TYPE_COLORS[node.type] || '#94A3B8')
  return {
    id: node.id,
    name: node.name,
    value: node.degree || 1,
    symbolSize,
    itemStyle: {
      color: waveMode ? 'rgba(15, 23, 42, 0.01)' : (isPathNode ? '#F97316' : nodeColor),
      borderColor: waveMode ? 'transparent' : (isPathNode ? '#FDE68A' : '#fff'),
      borderWidth: waveMode ? 0 : (isPathNode ? 4 : 2),
      opacity: pathMode && !isPathNode ? 0.28 : (waveMode ? 0.01 : 1),
      shadowBlur: isPathNode ? 28 : (waveMode ? 0 : 10),
      shadowColor: isPathNode ? 'rgba(249, 115, 22, 0.95)' : 'rgba(99, 102, 241, 0.5)',
    },
    label: {
      show: !waveMode,
      position: 'inside',
      offset: props.showLabels ? [0, Math.round((nameGap + nameLineHeight) / 2)] : [0, 0],
      formatter: node.type === 'Chapter'
        ? `{name|${node.name}}`
        : props.showLabels
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
          fontSize: 12,
          fontWeight: 700,
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
    ...(waveMode ? { symbol: 'circle' } : {}),
    rawNode: node,
  }
}

function initChart() {
  if (!chartRef.value) return

  chartInstance.value = echarts.init(chartRef.value)
  chartInstance.value.on('click', (params: any) => {
    if (params.dataType === 'node' && params.data.rawNode) {
      if (clickTimer) clearTimeout(clickTimer)
      clickTimer = setTimeout(() => {
        clickTimer = null
        emit('nodeClick', params.data.rawNode)
      }, 220)
    }
  })
  chartInstance.value.on('dblclick', (params: any) => {
    if (params.dataType === 'node' && params.data.rawNode) {
      if (clickTimer) {
        clearTimeout(clickTimer)
        clickTimer = null
      }
      emit('nodeDblClick', params.data.rawNode)
    }
  })

  updateChart()
}

function updateChart() {
  if (!chartInstance.value || !props.data) return

  const filteredNodes = props.data.nodes.filter(node => (
    !props.activeTypes || props.activeTypes.size === 0 || props.activeTypes.has(node.type)
  ))
  const nodeIds = new Set(filteredNodes.map(node => node.id))
  const filteredEdges = props.data.edges.filter(edge => (
    nodeIds.has(edge.source) && nodeIds.has(edge.target)
  ))
  const nodes = filteredNodes.map(buildChartNode)
  const links = filteredEdges.map(edge => {
    const relationName = edge.relationship_name.trim()
    return {
      source: edge.source,
      target: edge.target,
      value: relationName,
      // 边统一由下层 SVG 绘制，ECharts 仅保留 links 参与力导布局。
      symbol: ['none', 'none'],
      symbolSize: [0, 0],
      lineStyle: { opacity: 0 },
    }
  })

  chartInstance.value.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => (
        params.dataType === 'node' ? params.data.name : (params.data.value || '')
      ),
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links,
        roam: true,
        force: {
          repulsion: 800,
          edgeLength: 200,
          gravity: 0.1,
        },
        emphasis: props.showMasteryWave
          ? { focus: 'none', lineStyle: { width: 0, opacity: 0 } }
          : { focus: 'adjacency', lineStyle: { width: 0, opacity: 0 } },
        edgeLabel: {
          show: false,
          formatter: (params: any) => params.data?.value || '',
        },
      },
    ],
  })
  scheduleOverlayUpdate()
}

function createWaveOverlayNode(node: GraphNode, symbolSize: number): HTMLElement {
  const mastery = Math.max(0, Math.min(1, node.mastery || 0))
  const waveTop = Math.round((1 - mastery) * 100)
  const waveY = Math.max(6, Math.min(94, waveTop + 2))
  const color = TYPE_COLORS[node.type] || '#94A3B8'
  const pathMode = Boolean(props.highlightedNodeIds?.size)
  const isPathNode = props.highlightedNodeIds?.has(node.id) ?? false
  const pathColor = isPathNode ? '#F97316' : color
  const clipId = `wave-${encodeURIComponent(node.id).replace(/%/g, '')}`
  const wrapper = document.createElement('div')
  wrapper.className = 'kg-wave-node'
  wrapper.dataset.nodeId = node.id
  wrapper.dataset.signature = `${node.mastery ?? 0}:${node.degree ?? 0}:${isPathNode}`
  wrapper.style.width = `${symbolSize}px`
  wrapper.style.height = `${symbolSize + 36}px`
  wrapper.style.opacity = pathMode && !isPathNode ? '0.28' : '1'

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('viewBox', '0 0 100 100')
  svg.setAttribute('width', `${symbolSize}`)
  svg.setAttribute('height', `${symbolSize}`)
  svg.classList.add('kg-wave-svg')
  svg.innerHTML = `
    <defs><clipPath id="${clipId}"><circle cx="50" cy="50" r="44" /></clipPath></defs>
    <circle cx="50" cy="50" r="46" fill="${color}" opacity="0.22" />
    <circle cx="50" cy="50" r="44" fill="#0f172a" opacity="0.72" />
    <g clip-path="url(#${clipId})">
      <rect x="-100" y="${waveY + 4}" width="300" height="${Math.max(0, 96 - waveY)}" fill="${color}" opacity="0.9" />
      <path d="M-100 ${waveY} Q-75 ${waveY - 8} -50 ${waveY} T0 ${waveY} T50 ${waveY} T100 ${waveY} T150 ${waveY} T200 ${waveY} V100 H-100 Z" fill="${color}" opacity="0.86">
        <animateTransform attributeName="transform" type="translate" values="0 2; 50 -3; 100 2" dur="2.4s" repeatCount="indefinite" />
      </path>
      <path d="M-100 ${waveY + 8} Q-75 ${waveY + 1} -50 ${waveY + 8} T0 ${waveY + 8} T50 ${waveY + 8} T100 ${waveY + 8} T150 ${waveY + 8} T200 ${waveY + 8} V100 H-100 Z" fill="${color}" opacity="0.42">
        <animateTransform attributeName="transform" type="translate" values="0 -1; 50 3; 100 -1" dur="3.1s" repeatCount="indefinite" />
      </path>
      <path d="M-100 ${waveY + 2} Q-75 ${waveY - 6} -50 ${waveY + 2} T0 ${waveY + 2} T50 ${waveY + 2} T100 ${waveY + 2} T150 ${waveY + 2} T200 ${waveY + 2}" fill="none" stroke="#fff" stroke-opacity="0.76" stroke-width="2.2">
        <animateTransform attributeName="transform" type="translate" values="0 2; 50 -3; 100 2" dur="2.4s" repeatCount="indefinite" />
      </path>
      <path d="M-100 ${waveY + 10} Q-75 ${waveY + 5} -50 ${waveY + 10} T0 ${waveY + 10} T50 ${waveY + 10} T100 ${waveY + 10} T150 ${waveY + 10} T200 ${waveY + 10}" fill="none" stroke="#fff" stroke-opacity="0.3" stroke-width="1.4">
        <animateTransform attributeName="transform" type="translate" values="0 -1; 50 3; 100 -1" dur="3.1s" repeatCount="indefinite" />
      </path>
    </g>
    <circle cx="50" cy="50" r="44" fill="none" stroke="#fff" stroke-opacity="0.8" stroke-width="2" />
    <circle class="kg-wave-pulse" cx="50" cy="50" r="48" fill="none" stroke="${pathColor}" stroke-opacity="${isPathNode ? '0.95' : '0.32'}" stroke-width="${isPathNode ? '5' : '2'}" />
    <text x="50" y="57" text-anchor="middle" class="kg-wave-percent">${Math.round(mastery * 100)}%</text>
  `
  wrapper.appendChild(svg)

  const name = document.createElement('div')
  name.className = 'kg-wave-name'
  name.textContent = node.name
  name.style.display = props.showLabels ? '' : 'none'
  wrapper.appendChild(name)
  return wrapper
}

function clearWaveOverlayNodes() {
  waveOverlayNodes.clear()
  if (waveOverlayRef.value) waveOverlayRef.value.replaceChildren()
}

function clearEdgeOverlay() {
  edgeOverlayGroups.clear()
  edgeOverlayMode = null
  if (edgeOverlayRef.value) edgeOverlayRef.value.replaceChildren()
}

function clearOverlays() {
  if (waveOverlayFrame !== null) {
    cancelAnimationFrame(waveOverlayFrame)
    waveOverlayFrame = null
  }
  clearWaveOverlayNodes()
  clearEdgeOverlay()
}

function collectGraphPositions(): Map<string, [number, number]> {
  const positions = new Map<string, [number, number]>()
  if (!chartInstance.value) return positions
  const seriesModel = (chartInstance.value as any).getModel?.().getSeriesByIndex(0) as any
  const data = seriesModel?.getData?.()
  if (!data) return positions

  for (let index = 0; index < data.count(); index += 1) {
    const graphic = data.getItemGraphicEl(index) as any
    const layout = data.getItemLayout(index) as [number, number] | undefined
    const point = graphic?.transformCoordToGlobal?.(0, 0) || layout
    if (!point || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) continue
    positions.set(String(data.getId(index)), [point[0], point[1]])
  }
  return positions
}

function updateWaveOverlayPositions(positions: Map<string, [number, number]>) {
  if (!props.showMasteryWave || !waveOverlayRef.value) return

  const nodeMap = new Map(props.data.nodes.map(node => [node.id, node]))
  const activeIds = new Set<string>()
  for (const [nodeId, point] of positions) {
    const node = nodeMap.get(nodeId)
    if (!node || node.type === 'Chapter') continue
    activeIds.add(nodeId)

    const signature = `${node.mastery ?? 0}:${node.degree ?? 0}:${props.highlightedNodeIds?.has(node.id) ?? false}`
    let overlayNode = waveOverlayNodes.get(nodeId)
    if (!overlayNode || overlayNode.dataset.signature !== signature) {
      overlayNode?.remove()
      const symbolSize = Math.max(30, Math.min(70, 20 + (node.degree || 0) * 3))
      overlayNode = createWaveOverlayNode(node, symbolSize)
      waveOverlayNodes.set(nodeId, overlayNode)
      waveOverlayRef.value.appendChild(overlayNode)
    }
    const pathMode = Boolean(props.highlightedNodeIds?.size)
    const isPathNode = props.highlightedNodeIds?.has(node.id) ?? false
    overlayNode.style.opacity = pathMode && !isPathNode ? '0.28' : '1'
    const name = overlayNode.querySelector('.kg-wave-name') as HTMLElement | null
    if (name) name.style.display = props.showLabels ? '' : 'none'
    // 定位的是水波纹圆本身，而不是包含下方名称的整个容器，保证边的中心线
    // 与节点视觉圆心重合。
    const symbolSize = Math.max(30, Math.min(70, 20 + (node.degree || 0) * 3))
    overlayNode.style.transform = `translate(${point[0] - symbolSize / 2}px, ${point[1] - symbolSize / 2}px)`
  }

  for (const [nodeId, overlayNode] of waveOverlayNodes) {
    if (!activeIds.has(nodeId)) {
      overlayNode.remove()
      waveOverlayNodes.delete(nodeId)
    }
  }
}

function createEdgeOverlayGroup(edge: { source: string; target: string; relationship_name: string }): SVGGElement {
  const relationColor = getRelationColor(edge)
  const relationName = edge.relationship_name.trim()
  const isDependency = DEPENDENCY_RELATIONS.has(relationName)
  const isStructural = relationName === '包含'
  const isPathEdge = props.highlightedEdgeIds?.has(edgeKey(edge)) ?? false
  const group = document.createElementNS('http://www.w3.org/2000/svg', 'g')
  group.classList.add('kg-edge-group')

  const glow = document.createElementNS('http://www.w3.org/2000/svg', 'line')
  glow.classList.add('kg-edge-glow')
  glow.setAttribute('stroke', relationColor)
  glow.setAttribute('stroke-width', isPathEdge ? '15' : (isDependency || props.showMasteryWave ? '9' : '6'))
  glow.setAttribute('stroke-linecap', 'round')
  glow.setAttribute('opacity', isPathEdge ? '0.52' : (isDependency || props.showMasteryWave ? '0.24' : '0.12'))

  const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
  line.classList.add('kg-edge-core')
  line.setAttribute('stroke', relationColor)
  line.setAttribute('stroke-width', isPathEdge ? '5' : (isDependency || props.showMasteryWave ? '2.8' : '1.5'))
  line.setAttribute('stroke', isPathEdge ? '#F97316' : relationColor)
  line.setAttribute('stroke-linecap', 'round')
  const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon')
  arrow.classList.add('kg-edge-arrow')
  arrow.setAttribute('fill', isPathEdge ? '#F97316' : relationColor)
  if (isStructural) arrow.setAttribute('display', 'none')

  group.append(glow, line, arrow)
  return group
}

function getNodeRadius(node: GraphNode): number {
  const symbolSize = Math.max(30, Math.min(70, 20 + (node.degree || 0) * 3))
  // 水波纹的外圈比主体圆略小；教师端使用 ECharts 圆形节点的完整半径。
  return symbolSize * (props.showMasteryWave ? 0.48 : 0.5)
}

function updateEdgeOverlayPositions(positions: Map<string, [number, number]>) {
  if (!edgeOverlayRef.value) return

  const currentMode = Boolean(props.showMasteryWave)
  if (edgeOverlayMode !== null && edgeOverlayMode !== currentMode) clearEdgeOverlay()
  edgeOverlayMode = currentMode

  const activeEdgeIds = new Set<string>()
  const nodeMap = new Map(props.data.nodes.map(node => [node.id, node]))
  for (const edge of props.data.edges) {
    const source = positions.get(edge.source)
    const target = positions.get(edge.target)
    const sourceNode = nodeMap.get(edge.source)
    const targetNode = nodeMap.get(edge.target)
    if (!source || !target || !sourceNode || !targetNode || edge.source === edge.target) continue

    const [x1, y1] = source
    const [x2, y2] = target
    const dx = x2 - x1
    const dy = y2 - y1
    const length = Math.sqrt(dx * dx + dy * dy)
    if (length <= 1) continue
    const ux = dx / length
    const uy = dy / length
    const sourceRadius = getNodeRadius(sourceNode)
    const targetRadius = getNodeRadius(targetNode)
    if (length <= sourceRadius + targetRadius) continue

    // 按中心连线与两个节点圆的交点裁切，避免箭头尖端落到节点内部。
    const startX = x1 + ux * sourceRadius
    const startY = y1 + uy * sourceRadius
    const endX = x2 - ux * targetRadius
    const endY = y2 - uy * targetRadius
    const edgeId = `${edge.source}->${edge.target}:${edge.relationship_name}`
    activeEdgeIds.add(edgeId)
    let group = edgeOverlayGroups.get(edgeId)
    if (!group) {
      group = createEdgeOverlayGroup(edge)
      edgeOverlayGroups.set(edgeId, group)
      edgeOverlayRef.value.appendChild(group)
    }

    const arrowSize = 9
    const side = 4.5
    const bx = endX - ux * arrowSize
    const by = endY - uy * arrowSize
    const p1 = `${endX},${endY}`
    const p2 = `${bx - uy * side},${by + ux * side}`
    const p3 = `${bx + uy * side},${by - ux * side}`

    const glow = group.children[0] as SVGLineElement
    const line = group.children[1] as SVGLineElement
    const arrow = group.children[2] as SVGPolygonElement
    const relationName = edge.relationship_name.trim()
    const isDependency = DEPENDENCY_RELATIONS.has(relationName)
    const isPathEdge = props.highlightedEdgeIds?.has(edgeKey(edge)) ?? false
    const pathMode = Boolean(props.highlightedNodeIds?.size)
    const isDimmed = pathMode && !isPathEdge
    const relationColor = getRelationColor(edge)
    glow.setAttribute('stroke', isPathEdge ? '#F97316' : relationColor)
    glow.setAttribute('stroke-width', isPathEdge ? '15' : (isDependency || props.showMasteryWave ? '9' : '6'))
    glow.setAttribute('opacity', isPathEdge ? '0.52' : (isDimmed ? '0.04' : (isDependency || props.showMasteryWave ? '0.24' : '0.12')))
    line.setAttribute('stroke', isPathEdge ? '#F97316' : relationColor)
    line.setAttribute('stroke-width', isPathEdge ? '5' : (isDependency || props.showMasteryWave ? '2.8' : '1.5'))
    line.setAttribute('opacity', isDimmed ? '0.16' : '1')
    arrow.setAttribute('fill', isPathEdge ? '#F97316' : relationColor)
    arrow.setAttribute('opacity', isDimmed ? '0.1' : '0.96')
    for (const element of [glow, line]) {
      element.setAttribute('x1', String(startX))
      element.setAttribute('y1', String(startY))
      element.setAttribute('x2', String(endX))
      element.setAttribute('y2', String(endY))
    }
    arrow.setAttribute('points', `${p1} ${p2} ${p3}`)
  }

  for (const [edgeId, group] of edgeOverlayGroups) {
    if (!activeEdgeIds.has(edgeId)) {
      group.remove()
      edgeOverlayGroups.delete(edgeId)
    }
  }
}

function scheduleOverlayUpdate() {
  if (!chartInstance.value) return
  if (waveOverlayFrame !== null) return
  waveOverlayFrame = requestAnimationFrame(() => {
    waveOverlayFrame = null
    const positions = collectGraphPositions()
    if (props.showMasteryWave) updateWaveOverlayPositions(positions)
    else clearWaveOverlayNodes()
    updateEdgeOverlayPositions(positions)
    scheduleOverlayUpdate()
  })
}

function handleResize() {
  chartInstance.value?.resize()
  scheduleOverlayUpdate()
}

function resizeChartToContainer() {
  const chart = chartInstance.value
  const element = chartRef.value
  if (!chart || !element || element.clientWidth <= 0 || element.clientHeight <= 0) return
  chart.resize({ width: element.clientWidth, height: element.clientHeight })
  scheduleOverlayUpdate()
}

watch(
  () => [props.data, props.showLabels, props.activeTypes, props.showMasteryWave, props.highlightedNodeIds, props.highlightedEdgeIds],
  () => {
    updateChart()
    scheduleOverlayUpdate()
  },
  { deep: true },
)

onMounted(() => {
  initChart()
  // KnowledgeExplore uses nested flex containers. The initial mount can happen
  // before the chart wrapper has its final height, so keep ECharts in sync with
  // the actual canvas size instead of leaving force nodes on a single row.
  if (chartRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => resizeChartToContainer())
    resizeObserver.observe(chartRef.value)
  }
  requestAnimationFrame(() => resizeChartToContainer())
  scheduleOverlayUpdate()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (clickTimer) clearTimeout(clickTimer)
  clearOverlays()
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  resizeObserver?.disconnect()
  resizeObserver = null
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
.kg-chart-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
}
.kg-chart-2d {
  position: relative;
  width: 100%;
  height: 100%;
  background: transparent;
  z-index: 1;
}
:deep(.kg-edge-overlay) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
  z-index: 0;
}
:deep(.kg-edge-group) {
  pointer-events: none;
}
:deep(.kg-edge-glow) {
  fill: none;
  stroke-linecap: round;
  filter: blur(4px);
}
:deep(.kg-edge-core) {
  fill: none;
  stroke-linecap: round;
}
:deep(.kg-edge-arrow) {
  opacity: 0.96;
}
:deep(.kg-wave-overlay) {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
  z-index: 2;
}
:deep(.kg-wave-node) {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
  will-change: transform;
}
:deep(.kg-wave-svg) {
  display: block;
  overflow: visible;
  flex: none;
}
:deep(.kg-wave-percent) {
  fill: #fff;
  font-size: 25px;
  font-weight: 700;
  font-family: Arial, sans-serif;
  paint-order: stroke;
  stroke: rgba(15, 23, 42, 0.35);
  stroke-width: 1.5px;
}
:deep(.kg-wave-name) {
  max-width: 150px;
  margin-top: 2px;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
  white-space: normal;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.95);
}
:deep(.kg-wave-pulse) {
  transform-box: fill-box;
  transform-origin: center;
  animation: kg-wave-pulse 2.8s ease-in-out infinite;
}
@keyframes kg-wave-pulse {
  0%, 100% { transform: scale(0.96); opacity: 0.42; }
  50% { transform: scale(1.04); opacity: 0.08; }
}
</style>
