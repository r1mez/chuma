import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchGraphData, searchNodes, type GraphData, type GraphNode } from '@/api/knowledge'

export type GraphErrorType =
  | { type: 'network'; message: string }
  | { type: 'not_found'; message: string }
  | { type: 'server'; message: string }

export const useKnowledgeStore = defineStore('knowledge', () => {
  const graphData = ref<GraphData | null>(null)
  const loading = ref(false)
  const error = ref<GraphErrorType | null>(null)
  const selectedNode = ref<GraphNode | null>(null)
  const searchQuery = ref('')
  const activeTypes = ref<Set<string>>(new Set())

  const isEmpty = computed(() => !loading.value && !error.value && !graphData.value)
  const nodeCount = computed(() => graphData.value?.stats.total_nodes ?? 0)
  const edgeCount = computed(() => graphData.value?.stats.total_edges ?? 0)

  async function loadGraphData(datasetId = 'main') {
    loading.value = true
    error.value = null
    try {
      const data = await fetchGraphData(datasetId)
      if (!data.nodes || data.nodes.length === 0) {
        graphData.value = null
        error.value = { type: 'not_found', message: '该数据集还没有图谱数据' }
      } else {
        graphData.value = data
      }
    } catch (e: any) {
      if (e.message?.includes?.('Network') || e.code === 'ERR_NETWORK') {
        error.value = { type: 'network', message: '无法连接服务器' }
      } else {
        error.value = { type: 'server', message: e?.message || '服务端错误' }
      }
    } finally {
      loading.value = false
    }
  }

  async function searchNodesByQuery(query: string) {
    searchQuery.value = query
    if (!query.trim()) return
    try {
      const result = await searchNodes(query)
      return result.results
    } catch {
      return []
    }
  }

  function selectNode(node: GraphNode | null) {
    selectedNode.value = node
  }

  function toggleType(type: string) {
    const set = new Set(activeTypes.value)
    if (set.has(type)) set.delete(type)
    else set.add(type)
    activeTypes.value = set
  }

  return {
    graphData, loading, error, selectedNode, searchQuery, activeTypes,
    isEmpty, nodeCount, edgeCount,
    loadGraphData, searchNodesByQuery, selectNode, toggleType,
  }
})
