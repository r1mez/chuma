import { ref } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import type { GraphNode, GraphEdge } from '@/api/knowledge'
import type { KgHitNode } from '@/composables/useChat'

export interface SubgraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface DirectionalSubgraphs {
  hitNode: GraphNode
  upstream: SubgraphData
  downstream: SubgraphData
}

const MAX_HOP_NODES = 8

function bfsDirectional(
  hitNodeId: string,
  allNodes: GraphNode[],
  allEdges: GraphEdge[],
  direction: 'upstream' | 'downstream',
  maxHops: number = 2,
): SubgraphData {
  // upstream: follow edges where target === current node (incoming edges)
  // downstream: follow edges where source === current node (outgoing edges)
  const isUpstream = direction === 'upstream'

  const collectedNodes: GraphNode[] = []
  const collectedEdges: GraphEdge[] = []
  const nodeById = new Map(allNodes.map(n => [n.id, n]))

  let currentIds = new Set([hitNodeId])
  const visited = new Set([hitNodeId])

  for (let hop = 1; hop <= maxHops; hop++) {
    const nextIds = new Set<string>()

    // For each current node, find connected edges in the direction
    const candidates: { edge: GraphEdge; neighborId: string }[] = []
    for (const cid of currentIds) {
      for (const edge of allEdges) {
        if (isUpstream && edge.target === cid && !visited.has(edge.source)) {
          candidates.push({ edge, neighborId: edge.source })
        } else if (!isUpstream && edge.source === cid && !visited.has(edge.target)) {
          candidates.push({ edge, neighborId: edge.target })
        }
      }
    }

    // Sort by degree (high degree = important), limit to MAX_HOP_NODES
    candidates.sort((a, b) => {
      const aNode = nodeById.get(a.neighborId)
      const bNode = nodeById.get(b.neighborId)
      return (bNode?.degree ?? 0) - (aNode?.degree ?? 0)
    })
    const selected = candidates.slice(0, MAX_HOP_NODES)

    for (const { edge, neighborId } of selected) {
      if (!visited.has(neighborId)) {
        visited.add(neighborId)
        nextIds.add(neighborId)
        const node = nodeById.get(neighborId)
        if (node) collectedNodes.push(node)
        collectedEdges.push(edge)
      }
    }

    currentIds = nextIds
    if (currentIds.size === 0) break  // No more nodes to explore
  }

  return { nodes: collectedNodes, edges: collectedEdges }
}

export function useSubgraph() {
  const knowledgeStore = useKnowledgeStore()

  const subgraphs = ref<DirectionalSubgraphs | null>(null)
  const subgraphLoading = ref(false)
  const subgraphError = ref<string | null>(null)

  async function extractSubgraphs(hitNode: KgHitNode) {
    subgraphLoading.value = true
    subgraphError.value = null

    try {
      // Load full graph data (uses cache if already loaded for this graph)
      await knowledgeStore.loadGraphData(hitNode.graphName)

      const graphData = knowledgeStore.graphData
      if (!graphData || !graphData.nodes || !graphData.edges) {
        subgraphError.value = '图谱数据加载失败'
        subgraphLoading.value = false
        return
      }

      // Find the hit node in the full graph data (by id, fallback to name)
      let effectiveHitNode = graphData.nodes.find(n => n.id === hitNode.nodeId)
      if (!effectiveHitNode) {
        effectiveHitNode = graphData.nodes.find(n => n.name === hitNode.nodeName)
      }
      if (!effectiveHitNode) {
        subgraphError.value = `未找到知识点 "${hitNode.nodeName}" 的图谱数据`
        subgraphLoading.value = false
        return
      }

      const upstream = bfsDirectional(
        effectiveHitNode.id,
        graphData.nodes,
        graphData.edges,
        'upstream',
        2,
      )

      const downstream = bfsDirectional(
        effectiveHitNode.id,
        graphData.nodes,
        graphData.edges,
        'downstream',
        2,
      )

      subgraphs.value = {
        hitNode: effectiveHitNode,
        upstream,
        downstream,
      }
    } catch (e: any) {
      subgraphError.value = e.message || '子图提取失败'
    } finally {
      subgraphLoading.value = false
    }
  }

  function clearSubgraphs() {
    subgraphs.value = null
    subgraphLoading.value = false
    subgraphError.value = null
  }

  return {
    subgraphs,
    subgraphLoading,
    subgraphError,
    extractSubgraphs,
    clearSubgraphs,
  }
}
