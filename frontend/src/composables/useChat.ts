import { ref } from 'vue'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)

  async function sendMessage(content: string, mode: 'quick' | 'deep') {
    messages.value.push({ role: 'user', content })
    loading.value = true
    try {
      // TODO: 调用 AI 网关 API
      const endpoint = mode === 'quick' ? '/ai/chat/quick' : '/ai/chat/deep'
      // const response = await request.post(endpoint, { message: content })
      // messages.value.push({ role: 'assistant', content: response.answer, sources: response.sources })
    } finally {
      loading.value = false
    }
  }

  return { messages, loading, sendMessage }
}
