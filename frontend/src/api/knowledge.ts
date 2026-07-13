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

export async function fetchGraphData(datasetId = 'main'): Promise<GraphData> {
  return request.get('/kg/graph/data', { params: { dataset_id: datasetId } })
}

export async function searchNodes(query: string, datasetId = 'main'): Promise<SearchResult> {
  return request.get('/kg/graph/search', { params: { q: query, dataset_id: datasetId } })
}
