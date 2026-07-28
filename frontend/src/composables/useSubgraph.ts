import { ref } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import type { GraphNode, GraphEdge } from '@/api/knowledge'
import type { KgHitNode } from '@/composables/useChat'

export interface SubgraphNode extends GraphNode {
  /** 节点相对于命中节点的关系方向 */
  relation: 'upstream' | 'downstream' | 'both' | 'hit'
  /** BFS 跳数（0=命中节点, 1=直接相邻, 2=两跳） */
  hop: number
}

export interface SubgraphData {
  hitNode: SubgraphNode
  nodes: SubgraphNode[]
  edges: GraphEdge[]
}

const MAX_HOP_NODES = 8
const MAX_HOPS = 2

function bfsBidirectional(
  hitNodeId: string,
  allNodes: GraphNode[],
  allEdges: GraphEdge[],
): { nodes: SubgraphNode[]; edges: GraphEdge[] } {
  const nodeById = new Map(allNodes.map(n => [n.id, n]))
  const collectedEdges: GraphEdge[] = []
  const relationMap = new Map<string, { relation: Set<'upstream' | 'downstream'>; hop: number }>()

  // Initialize with hit node
  relationMap.set(hitNodeId, { relation: new Set(['hit'] as any), hop: 0 })

  let currentIds = new Set([hitNodeId])
  const visited = new Set([hitNodeId])

  for (let hop = 1; hop <= MAX_HOPS; hop++) {
    const nextIds = new Set<string>()
    const candidates: { edge: GraphEdge; neighborId: string; dir: 'upstream' | 'downstream' }[] = []

    for (const cid of currentIds) {
      for (const edge of allEdges) {
        // Upstream: edge.target === cid (incoming to current node)
        if (edge.target === cid && !visited.has(edge.source)) {
          candidates.push({ edge, neighborId: edge.source, dir: 'upstream' })
        }
        // Downstream: edge.source === cid (outgoing from current node)
        if (edge.source === cid && !visited.has(edge.target)) {
          candidates.push({ edge, neighborId: edge.target, dir: 'downstream' })
        }
      }
    }

    // Sort by degree (high degree = important), limit per hop
    candidates.sort((a, b) => {
      const aNode = nodeById.get(a.neighborId)
      const bNode = nodeById.get(b.neighborId)
      return (bNode?.degree ?? 0) - (aNode?.degree ?? 0)
    })
    const selected = candidates.slice(0, MAX_HOP_NODES)

    for (const { edge, neighborId, dir } of selected) {
      if (!visited.has(neighborId)) {
        visited.add(neighborId)
        nextIds.add(neighborId)

        // Track relation direction (may accumulate if reached from both sides)
        const existing = relationMap.get(neighborId)
        if (existing) {
          existing.relation.add(dir)
          existing.hop = Math.min(existing.hop, hop)
        } else {
          relationMap.set(neighborId, { relation: new Set([dir]), hop })
        }

        // Avoid duplicate edges
        if (!collectedEdges.some(e => e.source === edge.source && e.target === edge.target)) {
          collectedEdges.push(edge)
        }
      }
    }

    currentIds = nextIds
    if (currentIds.size === 0) break
  }

  // Build node list
  const nodes: SubgraphNode[] = []
  for (const [nid, info] of relationMap) {
    if (nid === hitNodeId) continue // hit node handled separately
    const raw = nodeById.get(nid)
    if (!raw) continue

    let relation: SubgraphNode['relation']
    if (info.relation.has('upstream') && info.relation.has('downstream')) {
      relation = 'both'
    } else if (info.relation.has('upstream')) {
      relation = 'upstream'
    } else {
      relation = 'downstream'
    }

    nodes.push({ ...raw, relation, hop: info.hop })
  }

  return { nodes, edges: collectedEdges }
}

export function useSubgraph() {
  const knowledgeStore = useKnowledgeStore()

  const subgraphs = ref<SubgraphData | null>(null)
  const subgraphLoading = ref(false)
  const subgraphError = ref<string | null>(null)

  async function extractSubgraphs(hitNode: KgHitNode) {
    subgraphLoading.value = true
    subgraphError.value = null

    try {
      await knowledgeStore.loadGraphData(hitNode.graphName)

      const graphData = knowledgeStore.graphData
      if (!graphData || !graphData.nodes || !graphData.edges) {
        subgraphError.value = '图谱数据加载失败'
        subgraphLoading.value = false
        return
      }

      // Find the hit node in the full graph data
      let rawHitNode = graphData.nodes.find(n => n.id === hitNode.nodeId)
      if (!rawHitNode) {
        rawHitNode = graphData.nodes.find(n => n.name === hitNode.nodeName)
      }
      if (!rawHitNode) {
        subgraphError.value = `未找到知识点 "${hitNode.nodeName}" 的图谱数据`
        subgraphLoading.value = false
        return
      }

      const { nodes, edges } = bfsBidirectional(
        rawHitNode.id,
        graphData.nodes,
        graphData.edges,
      )

      subgraphs.value = {
        hitNode: { ...rawHitNode, relation: 'hit', hop: 0 },
        nodes,
        edges,
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