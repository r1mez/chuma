# 快速回答（Quick Chat）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 AI 对话页面的"快速回答"功能——前端流式输出 + 后端代理转发 + 本地 Qwen3.5-9B 模型调用。

**Architecture:** 三层架构：前端 Vue (SSE 流式接收) → backend 网关 (httpx 代理转发，注入服务间认证) → ai 引擎 (调用 LLMClient.stream，纯 LLM 对话，不走 RAG)。

**Tech Stack:** Vue 3 + TypeScript + Element Plus (前端) / FastAPI + httpx (后端) / FastAPI + LLMClient (AI 引擎)

## Global Constraints

- 本地模型 API 地址：`http://10.16.75.254:8000/v1/chat/completions`
- 模型名称：`/home/ll_yqs2/models/Qwen3.5-9B`
- 无需 API Key 认证
- 支持 OpenAI 兼容格式 + SSE 流式输出
- 服务间认证：backend → ai 使用 `X-Service-Token` 请求头
- 前端使用 SSE (`fetch` + `ReadableStream`) 接收流式数据
- 支持多轮对话（历史消息一起发送）

## 文件结构

```
修改/创建的文件：
├── ai/app/config.py                    # 新增 QUICK_MODEL_* 配置项
├── ai/app/engines/llm/profiles.py      # 新增 quick_profile() 工厂函数
├── ai/app/schemas/rag.py               # 简化请求/响应 schema（去掉 sources/confidence）
├── ai/app/api/rag.py                   # 实现 /query/stream 流式端点
├── backend/app/api/ai_gateway.py       # 实现 /chat/quick 代理转发（SSE 透传）
├── frontend/src/api/ai.ts              # 实现流式 API 调用函数
├── frontend/src/composables/useChat.ts # 重写，支持流式输出
├── frontend/src/components/ChatMessage.vue      # 新建：消息气泡组件
├── frontend/src/components/ChatInput.vue        # 新建：输入框组件
└── frontend/src/pages/student/Chat.vue          # 重写：完整对话页面
```

---

### Task 1: 配置层 — 新增 QUICK_MODEL 配置

**Files:**
- Modify: `ai/app/config.py`
- Modify: `ai/app/engines/llm/profiles.py`

**Interfaces:**
- Produces: `quick_profile() -> ModelProfile` — 后续 Task 依赖此函数获取本地模型配置

- [ ] **Step 1: 在 config.py 中添加 QUICK_MODEL 配置项**

```python
# ai/app/config.py — 在 REMOTE_MODEL_* 后添加
class Settings(BaseSettings):
    # ... 现有配置 ...

    # 快速回答模型（内网部署的 Qwen3.5-9B）
    QUICK_MODEL_URL: str = "http://10.16.75.254:8000/v1"
    QUICK_MODEL_NAME: str = "/home/ll_yqs2/models/Qwen3.5-9B"
```

- [ ] **Step 2: 在 profiles.py 中添加 quick_profile() 工厂函数**

```python
def quick_profile() -> ModelProfile:
    """快速回答模型 profile（内网 Qwen3.5-9B）"""
    from app.config import settings
    return ModelProfile(
        base_url=settings.QUICK_MODEL_URL,
        model_name=settings.QUICK_MODEL_NAME,
        timeout=60.0,
    )
```

- [ ] **Step 3: 验证配置可读取**

```bash
cd ai && python -c "from app.engines.llm.profiles import quick_profile; p = quick_profile(); print(p)"
```

Expected: 输出 `ModelProfile(base_url='http://10.16.75.254:8000/v1', model_name='/home/ll_yqs2/models/Qwen3.5-9B', ...)`

- [ ] **Step 4: Commit**

```bash
git add ai/app/config.py ai/app/engines/llm/profiles.py
git commit -m "feat(ai): add quick_profile for local Qwen3.5-9B model"
```

---

### Task 2: AI 引擎 — 实现流式问答端点

**Files:**
- Modify: `ai/app/schemas/rag.py`
- Modify: `ai/app/api/rag.py`

**Interfaces:**
- Consumes: `quick_profile()` from Task 1, `LLMClient.stream()` (existing)
- Produces: `POST /rag/query/stream` — SSE 流式端点，`data: {"content": "..."}` 格式

- [ ] **Step 1: 更新 schemas/rag.py，添加流式请求 schema**

```python
# ai/app/schemas/rag.py
from pydantic import BaseModel


class QuickChatRequest(BaseModel):
    """快速回答请求"""
    message: str
    history: list[dict] = []  # 多轮对话历史 [{"role": "user", "content": "..."}, ...]


class RAGQueryRequest(BaseModel):
    question: str
    mode: str = "deep"  # "quick" | "deep"


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
```

- [ ] **Step 2: 实现 rag.py 中的 /query/stream 端点**

```python
# ai/app/api/rag.py
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import quick_profile
from app.schemas.rag import QuickChatRequest

router = APIRouter()


@router.post("/query/stream")
async def quick_chat_stream(req: QuickChatRequest):
    """快速回答 — 流式输出（纯 LLM，不走 RAG）"""
    llm = LLMClient(default_profile=quick_profile())

    # 构建消息列表：system prompt + 历史 + 当前问题
    messages = [
        {"role": "system", "content": "你是础码，一个计算机科学学习智能助教，擅长408考研和数据库原理相关知识。请用简洁准确的中文回答用户的问题。"},
        *req.history,
        {"role": "user", "content": req.message},
    ]

    async def event_stream():
        async for chunk in llm.stream(messages):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 3: 验证端点可调用**

```bash
curl -N http://localhost:8001/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是银行家算法？", "history": []}'
```

Expected: SSE 流式输出，每行 `data: {"content": "..."}`，最后 `data: [DONE]`

- [ ] **Step 4: Commit**

```bash
git add ai/app/schemas/rag.py ai/app/api/rag.py
git commit -m "feat(ai): implement /rag/query/stream SSE endpoint for quick chat"
```

---

### Task 3: 后端网关 — 实现 SSE 透传代理

**Files:**
- Modify: `backend/app/api/ai_gateway.py`

**Interfaces:**
- Consumes: `POST /rag/query/stream` from Task 2
- Produces: `POST /api/ai/chat/quick` — SSE 透传，前端直接调用

- [ ] **Step 1: 实现 ai_gateway.py 中的 /chat/quick 端点**

```python
# backend/app/api/ai_gateway.py
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter()


def _ai_headers():
    return {"X-Service-Token": settings.AI_SERVICE_TOKEN}


@router.post("/chat/quick")
async def chat_quick(request: Request):
    """快速回答 — SSE 透传到 AI 引擎"""
    body = await request.json()

    async def proxy_stream():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{settings.AI_SERVICE_URL}/rag/query/stream",
                headers=_ai_headers(),
                json=body,
            ) as resp:
                async for line in resp.aiter_lines():
                    yield line + "\n"

    return StreamingResponse(
        proxy_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 2: 验证端到端代理**

```bash
curl -N http://localhost:8000/api/ai/chat/quick \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"message": "什么是死锁？", "history": []}'
```

Expected: SSE 流式输出从 backend 透传到终端

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/ai_gateway.py
git commit -m "feat(backend): implement /chat/quick SSE proxy to AI engine"
```

---

### Task 4: 前端 — 流式 API 调用函数

**Files:**
- Modify: `frontend/src/api/ai.ts`

**Interfaces:**
- Produces: `sendQuickMessage(message, history, onChunk, onDone)` — 流式调用函数，回调式接收 chunk

- [ ] **Step 1: 实现 ai.ts 中的流式调用函数**

```typescript
// frontend/src/api/ai.ts
const API_BASE = '/api'

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

/**
 * 快速回答 — 流式调用
 * @param message 用户消息
 * @param history 对话历史
 * @param onChunk 每收到一个 chunk 触发
 * @param onDone 流结束时触发
 * @param onError 错误时触发
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
      buffer = lines.pop() || ''  // 保留未完成的行

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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/ai.ts
git commit -m "feat(frontend): implement sendQuickMessage with SSE streaming"
```

---

### Task 5: 前端 — 重写 useChat composable

**Files:**
- Modify: `frontend/src/composables/useChat.ts`

**Interfaces:**
- Consumes: `sendQuickMessage()` from Task 4
- Produces: `useChat()` — `{ messages, loading, sendMessage, clearMessages }`

- [ ] **Step 1: 重写 useChat.ts**

```typescript
// frontend/src/composables/useChat.ts
import { ref } from 'vue'
import { sendQuickMessage, type ChatHistoryItem } from '@/api/ai'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export function useChat() {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const streamingContent = ref('')  // 流式输出中累积的内容

  async function sendMessage(content: string) {
    // 添加用户消息
    messages.value.push({ role: 'user', content })

    // 构建历史（不含当前正在流式输出的 assistant 消息）
    const history: ChatHistoryItem[] = messages.value
      .slice(0, -1)  // 排除刚加入的 user 消息（它会作为 message 参数发送）
      .map(m => ({ role: m.role, content: m.content }))

    loading.value = true
    streamingContent.value = ''

    // 先加入一个空的 assistant 消息，用于流式填充
    const assistantIdx = messages.value.length
    messages.value.push({ role: 'assistant', content: '' })

    await sendQuickMessage(
      content,
      history,
      // onChunk: 累积流式内容
      (chunk) => {
        streamingContent.value += chunk
        messages.value[assistantIdx].content = streamingContent.value
      },
      // onDone
      () => {
        loading.value = false
        streamingContent.value = ''
      },
      // onError
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/composables/useChat.ts
git commit -m "feat(frontend): rewrite useChat with streaming support"
```

---

### Task 6: 前端 — 消息气泡组件

**Files:**
- Create: `frontend/src/components/ChatMessage.vue`

**Interfaces:**
- Props: `message: ChatMessage`, `loading: boolean`
- Renders: 用户消息（右侧蓝色）/ 助手消息（左侧灰色）/ 加载动画

- [ ] **Step 1: 创建 ChatMessage.vue**

```vue
<!-- frontend/src/components/ChatMessage.vue -->
<template>
  <div class="chat-message" :class="message.role">
    <div class="avatar">
      <el-icon v-if="message.role === 'user'" :size="20"><User /></el-icon>
      <el-icon v-else :size="20"><Monitor /></el-icon>
    </div>
    <div class="bubble">
      <div v-if="loading && message.role === 'assistant' && !message.content" class="typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
      <div v-else class="content" v-html="renderContent(message.content)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { User, Monitor } from '@element-plus/icons-vue'
import type { ChatMessage } from '@/composables/useChat'

defineProps<{
  message: ChatMessage
  loading?: boolean
}>()

function renderContent(text: string): string {
  // 简单的换行转 <br>
  return text.replace(/\n/g, '<br>')
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.chat-message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.chat-message.user .avatar {
  background: #409eff;
  color: white;
}
.chat-message.assistant .avatar {
  background: #e4e7ed;
  color: #606266;
}
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
}
.chat-message.user .bubble {
  background: #409eff;
  color: white;
  border-top-right-radius: 4px;
}
.chat-message.assistant .bubble {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}
.typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatMessage.vue
git commit -m "feat(frontend): add ChatMessage bubble component"
```

---

### Task 7: 前端 — 输入框组件

**Files:**
- Create: `frontend/src/components/ChatInput.vue`

**Interfaces:**
- Props: `loading: boolean`
- Emits: `@send(content: string)`
- Renders: 输入框 + 发送按钮，Enter 发送，Shift+Enter 换行

- [ ] **Step 1: 创建 ChatInput.vue**

```vue
<!-- frontend/src/components/ChatInput.vue -->
<template>
  <div class="chat-input">
    <el-input
      v-model="input"
      type="textarea"
      :rows="2"
      :autosize="{ minRows: 1, maxRows: 4 }"
      placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
      @keydown="handleKeydown"
      :disabled="loading"
    />
    <el-button
      type="primary"
      :icon="Promotion"
      :loading="loading"
      :disabled="!input.trim()"
      @click="handleSend"
    >
      发送
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

const props = defineProps<{ loading: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const input = ref('')

function handleSend() {
  const text = input.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<style scoped>
.chat-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 16px;
  border-top: 1px solid #e4e7ed;
  background: white;
}
.chat-input .el-textarea {
  flex: 1;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ChatInput.vue
git commit -m "feat(frontend): add ChatInput component with Enter-to-send"
```

---

### Task 8: 前端 — 重写 Chat 页面

**Files:**
- Modify: `frontend/src/pages/student/Chat.vue`

**Interfaces:**
- Consumes: `useChat()` from Task 5, `ChatMessage` from Task 6, `ChatInput` from Task 7
- Renders: 完整对话页面（消息列表 + 输入框 + 模式切换预留）

- [ ] **Step 1: 重写 Chat.vue**

```vue
<!-- frontend/src/pages/student/Chat.vue -->
<template>
  <div class="chat-page">
    <!-- 顶部栏 -->
    <div class="chat-header">
      <h3>AI 助教</h3>
      <div class="header-actions">
        <el-tag type="success" effect="plain">快速回答</el-tag>
        <el-tag type="info" effect="plain" disabled>深度思考（开发中）</el-tag>
        <el-tag type="info" effect="plain" disabled>规划模式（开发中）</el-tag>
        <el-button text @click="clearMessages" :disabled="messages.length === 0">
          清空对话
        </el-button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>开始向 AI 助教提问吧！</p>
        <p class="hint">支持 408 考研、数据库原理等计算机科学问题</p>
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :message="msg"
        :loading="loading && i === messages.length - 1"
      />
    </div>

    <!-- 输入框 -->
    <ChatInput :loading="loading" @send="sendMessage" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { useChat } from '@/composables/useChat'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

const { messages, loading, sendMessage, clearMessages } = useChat()
const messagesRef = ref<HTMLElement>()

// 自动滚动到底部
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
// 流式输出时也要滚动
watch(
  () => messages.value[messages.value.length - 1]?.content,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}
.chat-header h3 {
  margin: 0;
  font-size: 16px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}
.empty-state p {
  margin: 8px 0 0;
  font-size: 14px;
}
.hint {
  font-size: 12px !important;
  color: #c0c4cc;
}
</style>
```

- [ ] **Step 2: 验证前端页面可访问**

```bash
cd frontend && npm run dev
```

访问 `http://localhost:5173/student/chat`，应看到对话界面。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/student/Chat.vue
git commit -m "feat(frontend): implement Chat page with streaming quick answer"
```

---

### Task 9: 端到端验证

**Files:** 无新增文件

- [ ] **Step 1: 启动所有服务**

```bash
# 终端 1: AI 引擎
cd ai && uvicorn app.main:app --reload --port 8001

# 终端 2: 后端
cd backend && uvicorn app.main:app --reload --port 8000

# 终端 3: 前端
cd frontend && npm run dev
```

- [ ] **Step 2: 验证 AI 引擎流式端点**

```bash
curl -N http://localhost:8001/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是银行家算法？", "history": []}'
```

Expected: SSE 流式输出，每行 `data: {"content": "..."}`，最后 `data: [DONE]`

- [ ] **Step 3: 验证后端代理透传**

```bash
curl -N http://localhost:8000/api/ai/chat/quick \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是死锁？", "history": []}'
```

Expected: 同样的 SSE 流式输出

- [ ] **Step 4: 验证前端多轮对话**

1. 访问 `http://localhost:5173/student/chat`
2. 输入 "什么是银行家算法？" → 应看到流式输出回答
3. 追问 "它和死锁有什么关系？" → 应看到基于上下文的回答
4. 点击 "清空对话" → 消息列表清空

- [ ] **Step 5: Final Commit**

```bash
git add -A
git commit -m "feat: complete quick chat feature with SSE streaming"
```
