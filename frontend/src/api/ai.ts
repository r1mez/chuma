import type { AgentEventV2 } from '@/types/agent'

const API_BASE = '/api'

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatChunk {
  content: string
  reasoning: string
}

export interface SuggestedQuestion {
  text: string
  node_id: string
  node_name: string
  node_type: string
  relation: 'upstream' | 'downstream' | 'both'
}

export interface LegacyAgentSSEEvent {
  type: 'tool_used' | 'tool_result' | 'content' | 'done' | 'error' | 'kg_hit' | 'suggested_questions'
  tool?: string
  query?: string
  preview?: string
  content?: string
  // kg_hit fields
  node_id?: string
  node_name?: string
  node_type?: string
  graph_name?: string
  // suggested_questions fields
  questions?: SuggestedQuestion[]
}

export type AgentSSEEvent = LegacyAgentSSEEvent | AgentEventV2

export interface AgentRequestOptions {
  agentId?: string
  conversationId?: string
  studentId?: number
  teacherId?: number
  classId?: number
  courseId?: number
}

export interface AgentConversationSummary {
  conversation_id: string
  title: string
  agent_id: string
  message_count: number
  last_message_at?: string | null
}

export interface AgentConversationDetail extends AgentConversationSummary {
  messages: ChatHistoryItem[]
}

async function agentApiRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token')
  const response = await fetch(`${API_BASE}${url}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export function listAgentConversations(limit = 30): Promise<AgentConversationSummary[]> {
  return agentApiRequest<AgentConversationSummary[]>(`/ai/agent/conversations?limit=${limit}`)
}

export function getAgentConversation(conversationId: string): Promise<AgentConversationDetail> {
  return agentApiRequest<AgentConversationDetail>(
    `/ai/agent/conversations/${encodeURIComponent(conversationId)}`,
  )
}

export function deleteAgentConversation(conversationId: string): Promise<{ deleted: boolean; conversation_id: string }> {
  return agentApiRequest<{ deleted: boolean; conversation_id: string }>(
    `/ai/agent/conversations/${encodeURIComponent(conversationId)}`,
    { method: 'DELETE' },
  )
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

/**
 * 智能体模式 Agent 对话 — 流式调用（支持工具调用）
 */
export async function sendAgentMessage(
  message: string,
  history: ChatHistoryItem[],
  kgGraphIds: number[],
  messageId: string,
  onEvent: (event: AgentSSEEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  signal?: AbortSignal,
  options: AgentRequestOptions = {},
): Promise<void> {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/ai/agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message,
        history,
        kg_graph_ids: kgGraphIds,
        message_id: messageId,
        conversation_id: options.conversationId,
        agent_id: options.agentId,
        student_id: options.studentId,
        teacher_id: options.teacherId,
        class_id: options.classId,
        course_id: options.courseId,
      }),
      signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const processEventBlock = (block: string): boolean => {
      const data = block
        .split(/\r?\n/)
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trimStart())
        .join('\n')

      if (!data) return false
      if (data === '[DONE]') {
        onDone()
        return true
      }

      try {
        onEvent(JSON.parse(data) as AgentSSEEvent)
      } catch (error) {
        console.warn('[Agent SSE] 无法解析事件', { data, error })
      }
      return false
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() || ''

      for (const block of blocks) {
        if (processEventBlock(block)) return
      }
    }

    buffer += decoder.decode()
    if (buffer.trim() && processEventBlock(buffer)) return

    onDone()
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
