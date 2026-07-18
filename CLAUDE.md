# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目展望

智教慧学 是一个面向计算机科学学科的 AI 智能助教助学平台，采用"双引擎"架构（助学引擎 + 助教引擎），面向数据结构、计算机网络、操作系统、计算机组成原理和数据库原理学习。

- **学生侧**：知识图谱探索、GraphRAG 智能问答、个性化学习计划、错题归因分析、渐进式解题引导
- **教师侧**：学情分析报告、学生画像、作业批改、教案推荐

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts + Monaco Editor |
| 后端 | FastAPI + SQLAlchemy + Alembic + PostgreSQL |
| AI 引擎 | GraphRAG + GNN + 微调小模型（本地）+ 远程大模型 API |
| 向量数据库 | ChromaDB |
| 缓存/队列 | Redis |
| 部署 | Docker Compose |

## Monorepo 结构

三个独立项目组成一个 Monorepo，通过 Docker Compose 统一编排：

- **frontend/** — Vue 3 前端应用
- **backend/** — FastAPI 后端服务（业务逻辑、数据库、认证）
- **ai/** — AI 引擎服务（GraphRAG、GNN、知识图谱构建、定时任务）

## 部署环境

**本项目在远程服务器 `10.16.75.254`（Ubuntu Linux）上运行**，当前目录为本地开发/代码同步目录。服务器配备 2× RTX 4090 (24GB) + 1× RTX A6000 (48GB)。

所有服务在远程服务器上通过独立进程运行（非 Docker Compose），代码位于 `~/data/Projects/chuma/`。

### 端口分配

| 服务 | 端口 | 用途 | 外部可访问 |
|------|------|------|-----------|
| **前端 (Vite)** | `8000` | Vue 3 前端页面 | ✅ |
| **后端 (FastAPI)** | `8006` | 业务 API 网关 | ❌ 内部 |
| **AI 引擎 (FastAPI)** | `8001` | GraphRAG / LLM 调用 | ❌ 内部 |
| **vLLM 模型服务** | `8002` | Qwen3.5-9B 推理 | ❌ 内部 |
| **OCR 模型服务 (vLLM)** | `8004` | PDF/图片 OCR 文档解析 | ❌ 内部 |

### 访问地址

- **前端页面**：http://10.16.75.254:8000
- **AI 助教对话**：http://10.16.75.254:8000/student/chat
- **后端 API**：http://10.16.75.254:8006/docs（内部）
- **AI 引擎**：http://10.16.75.254:8001/docs（内部）

### 服务调用链路

```
浏览器 (用户)
  → 前端 :8000 (Vite dev server)
    → 后端 :8006 (/api/ai/chat/quick)
      → AI 引擎 :8001 (/rag/query/stream)
        → vLLM :8002 (/v1/chat/completions)
          → Qwen3.5-9B 模型

PDF 文档处理
  → infer.py (--pdf)
    → vLLM :8004 (/v1/chat/completions)
      → MinerU2.5-Pro-2605-1.2B 模型
```

### 本地开发 vs 远程部署

- **当前目录**：本地开发/代码编辑目录，代码需同步到远程服务器后生效
- **远程服务器**：实际运行环境，各服务通过独立进程/conda 环境管理
- **快速回答模型**：内网 `10.16.75.254:8002` 部署的 Qwen3.5-9B（vLLM 服务）
- **OCR 模型**：内网 `10.16.75.254:8004` 部署的 MinerU2.5-Pro-2605-1.2B（vLLM 服务）

## 常用命令

### 启动各服务（远程服务器）

各服务在远程服务器上通过独立进程运行，代码位于 `~/data/Projects/chuma/`。

#### 1. vLLM 外部模型服务（端口 8002 / 8004）

两个模型共用 `chuma-llm` conda 环境，通过 vLLM 提供 OpenAI 兼容 API。

**1.1 LLM 模型（Qwen3.5-9B，端口 8002）：**

```bash
conda activate chuma-llm
export FLASHINFER_DISABLE_VERSION_CHECK=1
CUDA_VISIBLE_DEVICES=2 vllm serve ~/models/Qwen3.5-9B \
    --host 0.0.0.0 \
    --port 8002 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --reasoning-parser qwen3 \
    --trust-remote-code \
    --default-chat-template-kwargs '{"enable_thinking": false}'
```

**1.2 OCR 模型（MinerU2.5-Pro-2605-1.2B，端口 8004）：**

```bash
conda activate chuma-llm
CUDA_VISIBLE_DEVICES=2 vllm serve \
    /home/ll_yqs2/models/MinerU2.5-Pro-2605-1.2B \
    --port 8004 \
    --trust-remote-code \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.1 \
    --max-model-len 8192 \
    --max-num-seqs 8 \
    --enforce-eager
```

#### 2. AI 引擎（端口 8001）

```bash
conda activate chuma-ai
cd ~/data/Projects/chuma/ai
python -m uvicorn app.main:app --reload --port 8001
```

#### 3. 后端（端口 8006）

```bash
conda activate chuma-backend
cd ~/data/Projects/chuma/backend
python -m uvicorn app.main:app --reload --port 8006
```

#### 4. 前端（端口 8000）

```bash
cd ~/data/Projects/chuma/frontend
npm run dev -- --host 0.0.0.0
```

### 本地开发（代码编辑后同步到远程）

```bash
# 前端（本地开发服务器）
cd frontend
npm install
npm run dev            # http://localhost:5173

# 后端（本地调试，连接远程数据库需配置 .env）
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# AI 引擎（本地调试）
cd ai
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 数据库迁移

```bash
cd backend
alembic upgrade head                        # 执行迁移
alembic revision --autogenerate -m "描述"   # 生成迁移文件
```

## 模型信息

| 模型 | 路径 | 参数量 | 显存占用 | 运行 GPU | 端口 | 框架 |
|------|------|--------|----------|----------|------|------|
| Qwen3.5-9B | `/home/ll_yqs2/models/Qwen3.5-9B` | 9B | ~18GB | GPU 2 (RTX 4090) | 8002 | vLLM |
| MinerU2.5-Pro-2605-1.2B | `/home/ll_yqs2/models/MinerU2.5-Pro-2605-1.2B` | 1.2B | - | GPU 2 (RTX 4090) | 8004 | vLLM |

- **Qwen3.5-9B**：快速回答模型，OpenAI 兼容 API (`/v1/chat/completions`)
- **MinerU2.5-Pro-2605-1.2B**：PDF/图片 OCR 文档解析，OpenAI 兼容 API (`/v1/chat/completions`)
- **vLLM 环境变量**：启动前需设置 `FLASHINFER_DISABLE_VERSION_CHECK=1`

## 系统通信模式

```
frontend  ←── HTTP ──→  backend  ←── HTTP(同步)/Redis(异步) ──→  ai
```

| 类型 | 协议 | 用途 |
|------|------|------|
| 实时查询 | HTTP REST | RAG 问答、GNN 推荐（秒级响应） |
| 异步任务 | Redis 队列 | 知识图谱抽取（长耗时批处理） |
| 定时任务 | APScheduler | 每日画像更新、每日一题生成 |

### 服务间认证

backend → AI 引擎的 HTTP 调用通过 `X-Service-Token` 请求头进行服务间认证：

- `backend/app/api/ai_gateway.py` 在转发请求时注入 `X-Service-Token: <token>`
- `ai/app/dependencies.py` 中的 `verify_service_token()` 校验 token
- 两个服务通过各自的 `.env` 配置同一个 token 值（`AI_SERVICE_TOKEN` / `SERVICE_TOKEN`）
- `/health` 端点不经过认证，供 Docker 健康检查使用
- 测试时可通过 FastAPI 的 `app.dependency_overrides` 跳过校验

## 前端架构

技术栈：Vue 3 + TypeScript + Element Plus + ECharts + Monaco Editor + Pinia

```
frontend/src/
├── api/              # 后端 API 调用封装（按模块一一对应后端路由）
│   ├── auth.ts
│   ├── knowledge.ts
│   ├── learning.ts
│   ├── practice.ts
│   ├── teacher.ts
│   └── ai.ts         # SSE 流式聊天接口
├── components/       # 通用 UI 组件（ChatMessage 含 Markdown+LaTeX 渲染）
├── composables/      # Vue 3 组合式函数（useAuth、useChat 等）
├── layouts/          # 布局组件（DefaultLayout 学生侧 / TeacherLayout 教师侧）
├── pages/            # 页面组件
│   ├── auth/         # 登录、注册
│   ├── student/      # 仪表盘、图谱探索、练习、错题本、AI 对话、学习计划
│   └── teacher/      # 课程管理、学生管理、学情报告、预警、批改
├── router/           # Vue Router 路由配置
├── stores/           # Pinia 全局状态管理（auth、knowledge、learning）
├── utils/            # 工具函数（Axios 封装，含 JWT 注入和错误拦截）
├── App.vue
└── main.ts
```

### 前端开发要点

- Vite 开发服务器代理配置：`vite.config.ts` 中 `/api` 代理到 `http://localhost:8006`
- 前端端口：开发环境 5173，生产环境 80
- AI 对话组件 `ChatMessage.vue` 使用 `marked` 渲染 Markdown，`highlight.js` 代码高亮，`katex` 渲染 LaTeX 公式
- SSE 流式输出由 `api/ai.ts` 中的 `sendQuickMessage` 处理，解析 `data:` 前缀的 JSON 数据

## 后端架构

技术栈：FastAPI + SQLAlchemy + Alembic + PostgreSQL + JWT

采用**分层架构**（按技术层组织）：

```
backend/app/
├── api/              # HTTP 路由层
│   ├── auth.py           # 注册、登录、JWT 认证
│   ├── knowledge.py      # 知识图谱数据查询（供前端 ECharts 可视化）
│   ├── learning.py       # 学习计划、学习进度、学习历史
│   ├── practice.py       # 题目列表、做题提交、错题本、归因分析、渐进式提示
│   ├── teacher.py        # 班级管理、学情分析、预警、学生画像、作业管理
│   └── ai_gateway.py     # 代理转发到 AI 引擎服务（注入 X-Service-Token）
├── services/         # 业务逻辑层（每个路由模块对应一个 service）
├── models/           # SQLAlchemy ORM 模型
├── schemas/          # Pydantic 请求/响应数据校验模型
├── core/             # 基础设施
│   ├── config.py         # 环境变量配置（Pydantic Settings）
│   ├── database.py       # 异步数据库连接与会话管理
│   ├── security.py       # JWT 生成/验证、密码哈希
│   └── deps.py           # FastAPI 依赖注入（当前用户解析等）
└── main.py           # FastAPI 应用入口
```

### 后端开发要点

- 数据库使用异步 SQLAlchemy + asyncpg，通过 `core/database.py` 中的 `get_db()` 依赖注入
- JWT 认证：`core/security.py` 使用 `python-jose` + `passlib[bcrypt]`
- 当前用户解析：`core/deps.py` 中的 `get_current_user` 依赖，从 `Authorization: Bearer <token>` 头解析
- 配置从 `.env` 加载，`core/config.py` 使用 `pydantic-settings`
- Alembic 迁移配置在 `alembic.ini`，数据库 URL 从环境变量读取

## AI 引擎架构

技术栈：FastAPI + ChromaDB + PyTorch + PyG + APScheduler + Redis

承担**三类职责**：实时推理、异步批处理、定时任务。

```
ai/app/
├── api/              # HTTP 路由（由 backend 同步调用）
│   ├── rag.py            # GraphRAG 增强问答
│   ├── gnn.py            # GNN 题目推荐、教案推荐
│   └── kg.py             # 知识图谱抽取任务提交与状态查询
├── engines/          # 核心 AI 能力（纯逻辑，不依赖 HTTP/队列框架）
│   ├── graphrag/
│   │   ├── retriever.py      # 图检索（ChromaDB + 知识图谱结构遍历）
│   │   ├── generator.py      # LLM 生成（带来源标注）
│   │   └── prompts.py        # 提示词模板
│   ├── gnn/
│   │   ├── model.py          # GNN 模型定义
│   │   ├── trainer.py        # 模型训练
│   │   └── inference.py      # 推理（题目推荐 / 教案推荐）
│   └── llm/
│       ├── client.py         # 统一 LLM 客户端（chat/stream，含重试、超时）
│       └── profiles.py       # 模型端点配置（local_profile / remote_profile / quick_profile）
├── tasks/            # 异步任务 + 定时任务
│   ├── worker.py           # Redis 队列消费者
│   ├── scheduler.py        # 定时调度器（APScheduler）
│   ├── registry.py         # 任务注册中心（装饰器自发现）
│   ├── kg_extract.py       # 知识图谱抽取
│   ├── daily_profile.py    # 每日用户画像更新（凌晨 4:00）
│   └── daily_question.py   # 每日一题生成（凌晨 4:30）
├── schemas/          # 请求/响应 Pydantic 模型
├── dependencies.py   # 公共依赖（服务间认证：X-Service-Token）
└── config.py         # AI 引擎配置
```

### AI 引擎开发要点

- **LLM 客户端**：`engines/llm/client.py` 是统一入口，封装 HTTP 调用、重试、超时。支持 `chat()` 和 `stream()` 两种模式。
- **模型 Profile**：`engines/llm/profiles.py` 定义三种 profile：
  - `local_profile()` — 本地微调小模型（快速回答）
  - `remote_profile()` — 远程大模型 API（深度解答）
  - `quick_profile()` — 内网 Qwen3.5-9B（快速回答，当前默认）
- **任务注册中心**：`tasks/registry.py` 采用装饰器自发现模式。新增任务只需创建文件 + `@task_handler` 或 `@scheduled_task` 装饰器，无需修改 worker/scheduler。
- **定时任务**：`daily_profile.py`（凌晨 4:00）、`daily_question.py`（凌晨 4:30）通过 `@scheduled_task` 注册。
- **异步任务**：`kg_extract.py` 通过 `@task_handler("kg_extract")` 注册，由 Redis 队列触发。
- **服务间认证**：`dependencies.py` 中的 `verify_service_token` 校验 `X-Service-Token`，所有路由默认依赖此认证。

## 双模型策略

| 模式 | 触发方式 | 模型 | 场景 |
|------|---------|------|------|
| 快速问答 | 用户在 UI 主动选择 | 本地微调小模型 / 内网 Qwen3.5-9B | 基础概念问答，快速响应 |
| 深度解答 | 用户在 UI 主动选择 | GraphRAG + 远程大模型 | 需要知识检索、来源标注的复杂问题 |

快速回答当前实现：前端 `api/ai.ts` → backend `ai_gateway.py` → ai `rag.py` → `LLMClient.stream()` → SSE 返回。

## 数据存储

| 存储 | 技术 | 职责 | 管理者 |
|------|------|------|--------|
| 关系型数据库 | PostgreSQL | 用户、题目、做题记录、学习计划、班级、学情 | backend |
| 向量数据库 | ChromaDB | 知识图谱嵌入、文档向量（语义检索） | ai |
| 缓存/队列 | Redis | 会话缓存、异步任务队列、定时任务锁 | 两者共享 |

## 环境变量配置

复制 `.env.example` 为 `.env`，关键配置项：

- `DATABASE_URL` — PostgreSQL 连接串
- `REDIS_URL` — Redis 连接串
- `JWT_SECRET_KEY` — JWT 签名密钥
- `AI_SERVICE_TOKEN` / `SERVICE_TOKEN` — 服务间认证 token（两者必须一致）
- `QUICK_MODEL_URL` — 快速回答模型地址（`http://10.16.75.254:8002`，vLLM 运行的 Qwen3.5-9B）
- `OCR_MODEL_URL` — OCR 模型地址（`http://10.16.75.254:8004`，vLLM 运行的 MinerU2.5-Pro-2605-1.2B）
- `REMOTE_MODEL_API_KEY` / `REMOTE_MODEL_BASE_URL` / `REMOTE_MODEL_NAME` — 远程大模型
- `CHROMADB_HOST` / `CHROMADB_PORT` — ChromaDB 地址（Docker 内用 `chromadb:8000`，本地开发用 `localhost:8020`，远程服务器用 `10.16.75.254:8020`）