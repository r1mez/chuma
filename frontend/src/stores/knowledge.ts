import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const graphData = ref<{ nodes: any[]; edges: any[] } | null>(null)
  return { graphData }
})
