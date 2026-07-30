import { ref } from 'vue'
import { sendQuickMessage, sendDeepMessage, sendAgentMessage, type ChatHistoryItem, type ChatChunk, type AgentSSEEvent } from '@/api/ai'
import { useSubgraph } from '@/composables/useSubgraph'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  reasoning?: string
  toolCalls?: ToolCallStatus[]
}

export interface ToolCallStatus {
  tool: string
  query: string
  status: 'running' | 'done'
  preview?: string
}

export type ChatMode = 'quick' | 'deep' | 'agent'

export interface KgHitNode {
  nodeId: string
  nodeName: string
  nodeType: string
  graphName: string
}

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const streamingContent = ref('')
  const streamingReasoning = ref('')
  const chatMode = ref<ChatMode>('quick')
  const kgGraphIds = ref<number[]>([])
  const kgHitNode = ref<KgHitNode | null>(null)
  const subgraphPanelVisible = ref(false)
  const subgraphManuallyClosed = ref(false)
  const { subgraphs, subgraphLoading, subgraphError, extractSubgraphs, clearSubgraphs } = useSubgraph()

  async function sendMessage(content: string) {
    messages.value.push({ role: 'user', content })

    const history: ChatHistoryItem[] = messages.value
      .slice(0, -1)
      .map((m) => ({ role: m.role, content: m.content }))

    loading.value = true
    streamingContent.value = ''
    streamingReasoning.value = ''

    const assistantIdx = messages.value.length
    messages.value.push({ role: 'assistant', content: '', reasoning: '', toolCalls: [] })

    if (chatMode.value === 'agent') {
      await sendAgentMessage(
        content,
        history,
        kgGraphIds.value,
        (event: AgentSSEEvent) => {
          if (event.type === 'tool_used') {
            messages.value[assistantIdx].toolCalls!.push({
              tool: event.tool!,
              query: event.query || '',
              status: 'running',
            })
          } else if (event.type === 'tool_result') {
            const tcs = messages.value[assistantIdx].toolCalls!
            const last = tcs.find(tc => tc.status === 'running')
            if (last) {
              last.status = 'done'
              last.preview = event.preview
            }
          } else if (event.type === 'content') {
            streamingContent.value += event.content!
            messages.value[assistantIdx].content = streamingContent.value
          } else if (event.type === 'error') {
            messages.value[assistantIdx].content = `⚠️ 出错了：${event.content}`
          } else if (event.type === 'kg_hit') {
            // New subgraph hit — update panel unless user manually closed it this conversation
            if (!subgraphManuallyClosed.value) {
              kgHitNode.value = {
                nodeId: event.node_id!,
                nodeName: event.node_name!,
                nodeType: event.node_type!,
                graphName: event.graph_name!,
              }
              subgraphPanelVisible.value = true
              // Trigger subgraph extraction (async, doesn't block SSE)
              extractSubgraphs(kgHitNode.value)
            }
          }
        },
        () => {
          loading.value = false
          streamingContent.value = ''
          streamingReasoning.value = ''
        },
        (err) => {
          messages.value[assistantIdx].content = `⚠️ 出错了：${err.message}`
          loading.value = false
          streamingContent.value = ''
          streamingReasoning.value = ''
        },
      )
      return
    }

    const sendFn = chatMode.value === 'deep' ? sendDeepMessage : sendQuickMessage

    await sendFn(
      content,
      history,
      (chunk: ChatChunk) => {
        if (chunk.reasoning) {
          streamingReasoning.value += chunk.reasoning
          messages.value[assistantIdx].reasoning = streamingReasoning.value
        }
        if (chunk.content) {
          streamingContent.value += chunk.content
          messages.value[assistantIdx].content = streamingContent.value
        }
      },
      () => {
        loading.value = false
        streamingContent.value = ''
        streamingReasoning.value = ''
      },
      (err) => {
        messages.value[assistantIdx].content = `⚠️ 出错了：${err.message}`
        loading.value = false
        streamingContent.value = ''
        streamingReasoning.value = ''
      },
    )
  }

  function closeSubgraphPanel() {
    subgraphPanelVisible.value = false
    subgraphManuallyClosed.value = true
  }

  function clearMessages() {
    messages.value = []
    kgHitNode.value = null
    subgraphPanelVisible.value = false
    subgraphManuallyClosed.value = false  // Reset for new conversation
    clearSubgraphs()
  }

  return { messages, loading, sendMessage, clearMessages, chatMode, kgGraphIds, kgHitNode, subgraphPanelVisible, closeSubgraphPanel, subgraphs, subgraphLoading, subgraphError, extractSubgraphs }
}
