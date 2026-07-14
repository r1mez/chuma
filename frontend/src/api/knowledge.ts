import request from '@/utils/request'

export interface GraphNode {
  id: string
  name: string
  type: string
  description: string
  degree: number
}

export interface GraphEdge {
  source: string
  target: string
  relationship_name: string
  description?: string
}

export interface GraphStats {
  total_nodes: number
  total_edges: number
  node_types: Record<string, number>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: GraphStats
}

export interface SearchResult {
  results: Array<{
    id: string
    name: string
    type: string
    description: string
  }>
}

export interface KgGraphInfo {
  id: number
  graph_name: string
  original_filename: string
  node_count: number
  edge_count: number
  chunk_count: number
  status: 'pending' | 'completed' | 'failed'
  created_at: string
}

export async function fetchGraphList(): Promise<KgGraphInfo[]> {
  return request.get('/knowledge/graphs')
}

export async function fetchGraphData(graphName?: string): Promise<GraphData> {
  const params: Record<string, string> = {}
  if (graphName) params.graph_name = graphName
  return request.get('/kg/graph/data', { params })
}

export async function searchNodes(query: string, graphName?: string): Promise<SearchResult> {
  const params: Record<string, string> = { q: query }
  if (graphName) params.graph_name = graphName
  return request.get('/kg/graph/search', { params })
}

export async function deleteGraph(graphId: number): Promise<{ status: string; graph_id: number }> {
  return request.delete(`/knowledge/graphs/${graphId}`)
}
