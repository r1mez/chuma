import type { GraphData, GraphNode } from '@/api/knowledge'

function nodeRank(node: GraphNode): number {
  return node.degree ?? 0
}

export function rankNeighborIds(
  anchorId: string,
  neighborIds: Iterable<string>,
  data: GraphData,
  limit = Number.POSITIVE_INFINITY,
): string[] {
  const nodeMap = new Map(data.nodes.map(node => [node.id, node]))
  return Array.from(new Set(neighborIds))
    .filter(id => id !== anchorId && nodeMap.get(id)?.type !== 'Chapter')
    .sort((left, right) => {
      const a = nodeMap.get(left)
      const b = nodeMap.get(right)
      if (!a && !b) return left.localeCompare(right)
      if (!a) return 1
      if (!b) return -1
      return nodeRank(b) - nodeRank(a) || a.name.localeCompare(b.name, 'zh-CN')
    })
    .slice(0, Number.isFinite(limit) ? limit : undefined)
}
