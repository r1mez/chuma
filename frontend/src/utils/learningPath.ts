import type { GraphData, GraphEdge, GraphNode } from '@/api/knowledge'

/** Relations whose direction is prerequisite -> dependent knowledge point. */
export const DEPENDENCY_RELATIONS = new Set(['依赖', '前提'])

export function getGraphEdgeKey(edge: Pick<GraphEdge, 'source' | 'target' | 'relationship_name'>): string {
  return `${edge.source}->${edge.target}:${edge.relationship_name}`
}

export interface LearningPath {
  targetId: string
  nodeIds: string[]
  edgeIds: string[]
  blockingNodeIds: string[]
}

/**
 * Build a prerequisite-first path for a target node.
 *
 * The KG extraction prompt defines dependency edges as source prerequisite ->
 * target dependent node. A DFS post-order gives a stable prerequisite-first
 * order while the visited set also makes the function safe for cyclic data.
 */
export function buildLearningPath(
  data: GraphData,
  targetId: string,
  masteryByNodeName: Record<string, number> = {},
  masteryThreshold = 0.6,
): LearningPath {
  const nodeMap = new Map(data.nodes.map(node => [node.id, node]))
  const incoming = new Map<string, GraphEdge[]>()

  for (const edge of data.edges) {
    if (!DEPENDENCY_RELATIONS.has(edge.relationship_name.trim())) continue
    if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target)) continue
    const edges = incoming.get(edge.target) ?? []
    edges.push(edge)
    incoming.set(edge.target, edges)
  }

  const orderedNodeIds: string[] = []
  const visited = new Set<string>()
  const visit = (nodeId: string) => {
    if (visited.has(nodeId)) return
    visited.add(nodeId)

    const prerequisites = [...(incoming.get(nodeId) ?? [])].sort((a, b) => {
      const aNode = nodeMap.get(a.source)
      const bNode = nodeMap.get(b.source)
      const aMastery = masteryByNodeName[aNode?.name ?? ''] ?? 0
      const bMastery = masteryByNodeName[bNode?.name ?? ''] ?? 0
      return aMastery - bMastery || (aNode?.name ?? '').localeCompare(bNode?.name ?? '')
    })
    for (const edge of prerequisites) visit(edge.source)
    orderedNodeIds.push(nodeId)
  }

  if (nodeMap.has(targetId)) visit(targetId)

  const nodeIdSet = new Set(orderedNodeIds)
  const edgeIds = data.edges
    .filter(edge => (
      DEPENDENCY_RELATIONS.has(edge.relationship_name.trim())
      && nodeIdSet.has(edge.source)
      && nodeIdSet.has(edge.target)
    ))
    .map(getGraphEdgeKey)

  const blockingNodeIds = orderedNodeIds.filter(nodeId => {
    const node = nodeMap.get(nodeId)
    return (masteryByNodeName[node?.name ?? ''] ?? 0) < masteryThreshold
  })

  return {
    targetId,
    nodeIds: orderedNodeIds,
    edgeIds,
    blockingNodeIds,
  }
}

export function getLearningPathLabel(path: LearningPath, data: GraphData): string {
  const nodeMap = new Map(data.nodes.map(node => [node.id, node]))
  const names = path.nodeIds
    .map(id => nodeMap.get(id)?.name)
    .filter((name): name is string => Boolean(name))
  return names.join(' → ')
}
