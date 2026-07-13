const API_BASE = '/api'

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatChunk {
  content: string
  reasoning: string
}

/**
 * 快速回答 — 流式调用
 */
export async function sendQuickMessage(
  message: string,
  history: ChatHistoryItem[],
  onChunk: (chunk: ChatChunk) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): Promise<void> {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/ai/chat/quick`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, history }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue

        const data = trimmed.slice(6)
        if (data === '[DONE]') {
          onDone()
          return
        }

        try {
          const parsed = JSON.parse(data) as ChatChunk
          if (parsed.content || parsed.reasoning) {
            onChunk(parsed)
          }
        } catch {
          // 忽略解析错误
        }
      }
    }

    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}

/**
 * 深度解答 — 流式调用（调用 DeepSeek）
 */
export async function sendDeepMessage(
  question: string,
  history: ChatHistoryItem[],
  onChunk: (chunk: ChatChunk) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): Promise<void> {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/ai/chat/deep`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question, history }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed || !trimmed.startsWith('data: ')) continue

        const data = trimmed.slice(6)
        if (data === '[DONE]') {
          onDone()
          return
        }

        try {
          const parsed = JSON.parse(data) as ChatChunk
          if (parsed.content || parsed.reasoning) {
            onChunk(parsed)
          }
        } catch {
          // 忽略解析错误
        }
      }
    }

    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
