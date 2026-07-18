import { ref } from 'vue'
import { sendQuickMessage, sendDeepMessage, sendAgentMessage, type ChatHistoryItem, type ChatChunk, type AgentSSEEvent } from '@/api/ai'

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

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const streamingContent = ref('')
  const streamingReasoning = ref('')
  const chatMode = ref<ChatMode>('quick')

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

  function clearMessages() {
    messages.value = []
  }

  return { messages, loading, sendMessage, clearMessages, chatMode }
}
