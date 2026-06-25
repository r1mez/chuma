import { ref } from 'vue'
import { sendQuickMessage, type ChatHistoryItem } from '@/api/ai'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const streamingContent = ref('')

  async function sendMessage(content: string) {
    messages.value.push({ role: 'user', content })

    const history: ChatHistoryItem[] = messages.value
      .slice(0, -1)
      .map((m) => ({ role: m.role, content: m.content }))

    loading.value = true
    streamingContent.value = ''

    const assistantIdx = messages.value.length
    messages.value.push({ role: 'assistant', content: '' })

    await sendQuickMessage(
      content,
      history,
      (chunk) => {
        streamingContent.value += chunk
        messages.value[assistantIdx].content = streamingContent.value
      },
      () => {
        loading.value = false
        streamingContent.value = ''
      },
      (err) => {
        messages.value[assistantIdx].content = `⚠️ 出错了：${err.message}`
        loading.value = false
        streamingContent.value = ''
      },
    )
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, loading, sendMessage, clearMessages }
}
