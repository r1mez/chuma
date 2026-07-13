import { ref } from 'vue'
import { sendQuickMessage, sendDeepMessage, type ChatHistoryItem, type ChatChunk } from '@/api/ai'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  reasoning?: string  // 思考过程（仅深度思考模式的 assistant 消息有）
}

export type ChatMode = 'quick' | 'deep'

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
    messages.value.push({ role: 'assistant', content: '', reasoning: '' })

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
