const API_BASE = '/api'

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

/**
 * 快速回答 — 流式调用
 */
export async function sendQuickMessage(
  message: string,
  history: ChatHistoryItem[],
  onChunk: (content: string) => void,
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
          const parsed = JSON.parse(data)
          if (parsed.content) {
            onChunk(parsed.content)
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
