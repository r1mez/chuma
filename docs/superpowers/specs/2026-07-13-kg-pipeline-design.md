# 知识图谱自动构建 Pipeline 设计文档

> 日期：2026-07-13
> 状态：已批准

## 1. 概述

本文档描述了一个端到端的知识图谱构建 Pipeline，用于从原始文档（PDF、Word 等）中自动提取并构建计算机学科知识图谱，最终持久化到 PostgreSQL + Apache AGE 扩展。

### 1.1 核心流程

```
原始文档 (PDF/图片)
  → [阶段 1] MinerU OCR 解析 → Markdown
  → [阶段 2] 语义切片 → LLM 实体/关系抽取 → NetworkX 图构建
  → [阶段 3] Apache AGE 持久化 (Vertices + Edges)
```

### 1.2 设计原则

- **模块化**：五个独立模块（Chunking、Extraction、GraphBuilder、Storage、Pipeline），每层职责唯一
- **可溯源**：每个实体标注来源切片索引，支持回溯到原始文档
- **高容错**：每个阶段有独立异常处理，失败时可明确报告故障点
- **可扩展**：基于 Cognee v1.2.2 架构参考设计，未来可增加向量层或查询层

## 2. 代码位置

所有代码位于 AI 引擎服务的 `ai/app/kg_pipeline/` 模块：

```
ai/app/kg_pipeline/
├── __init__.py             # 导出核心类
├── models.py               # Pydantic 数据模型
├── chunking.py             # Markdown 文本切片
├── extraction.py           # LLM 实体/关系抽取
├── graph_builder.py        # NetworkX 内存图构建与去重
├── storage.py              # Apache AGE 持久化
├── pipeline.py             # Pipeline 编排调度
└── prompts/
    ├── __init__.py
    └── kg_extraction.txt   # LLM 抽取提示词
```

### 2.1 已有依赖复用

| 已有模块 | 用途 | 路径 |
|---------|------|------|
| OCR Service | 文档 → Markdown | `ai/app/ocr/service.py` |
| LLM Client | LLM 调用 | `ai/app/engines/llm/client.py` |
| Model Profile | LLM 配置 | `ai/app/engines/llm/profiles.py` |
| Task Registry | 异步任务注册 | `ai/app/tasks/registry.py` |
| Settings | 环境变量配置 | `ai/app/config.py` |

## 3. 数据模型

### 3.1 EntityType 枚举

```python
class EntityType(str, Enum):
    CONCEPT = "Concept"          # 基础理论概念
    ALGORITHM = "Algorithm"      # 具体算法
    DATA_STRUCTURE = "DataStructure"  # 数据结构
    PROTOCOL = "Protocol"        # 网络协议
    PRINCIPLE = "Principle"      # 原理/定律
    TERM = "Term"                # 专业术语
    TECHNOLOGY = "Technology"    # 具体技术/系统
    MODEL = "Model"              # 模型/架构
```

### 3.2 核心模型

```python
class KGNode(BaseModel):
    """节点 — 对应 AGE Vertex"""
    id: str
    name: str
    type: EntityType
    description: str
    source_chunk_index: int | None = None

class KGEdge(BaseModel):
    """边 — 对应 AGE Edge"""
    source_node_id: str
    target_node_id: str
    relationship_name: str      # LLM 自由生成，snake_case
    description: str | None

class KnowledgeGraph(BaseModel):
    """单切片知识图谱"""
    nodes: list[KGNode]
    edges: list[KGEdge]

class DocumentChunk(BaseModel):
    """文档切片"""
    id: str
    text: str
    chunk_index: int
    chunk_size: int
```

## 4. 切片策略 (Chunking)

### 4.1 实现

参考 Cognee 的 `chunk_by_paragraph` + `chunk_by_sentence` 策略，适配 Markdown：

1. 按 Markdown 标题（`# / ## / ###`）分割为 sections
2. 对每个 section 按句子粒度切分（`chunk_by_sentence`）
3. 聚合句子为 chunks，每块不超过 `max_chunk_size`
4. **不跨越标题边界**，保证语义完整性

### 4.2 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_chunk_size` | 1024 tokens | 适合计算机教材段落长度 |
| `batch_paragraphs` | True | 聚合短段落避免碎片 |

### 4.3 对比 Cognee

| 维度 | Cognee | 本设计 |
|------|--------|--------|
| max_chunk_size | 512 tokens | 1024 tokens |
| Markdown 感知 | 否 | 是（按标题分割） |
| 输出格式 | DocumentChunk 对象 | DocumentChunk 对象 |

## 5. LLM 抽取 (Extraction)

### 5.1 Prompt 设计

**System Prompt** 要求 LLM：
- 从 8 种预定义实体类型中选择
- 实体 ID 使用最标准的中文名称
- 关系名为 `snake_case`
- `description` 必须为具体描述（使用端点名称）
- 只抽取文本中明确提到的内容

**User Prompt**：传入切片文本。

### 5.2 调用策略

- 模型：Qwen3.5-9B（通过 `quick_profile()`）
- 方式：`LLMClient.chat()` + JSON 输出
- Temperature：0.1（保证抽取一致性）
- 后校验：Pydantic `KnowledgeGraph` 模型验证

### 5.3 为什么不用 structured_output / function calling

`LLMClient.chat()` + Pydantic 后验：
- 兼容所有模型（Qwen3.5-9B、DeepSeek、本地微调模型）
- 不需要额外依赖（Instructor、LangChain 等）
- vLLM 的 JSON mode 已足够保证格式

### 5.4 JSON 解析策略

LLM 返回的文本可能包含 markdown 包裹的 JSON（```json ... ```），解析流程：
1. 尝试直接 `json.loads()`
2. 若失败，正则提取 ```json(...)``` 或 ```(...)``` 代码块内容
3. 若仍失败，`LlmExtractionError` 并记录原始文本到日志

使用 `temperature=0.1` + vLLM JSON mode 可大幅降低格式错误率。

## 6. 图构建 (Graph Builder)

### 6.1 实现

使用 NetworkX `DiGraph` 作为内存中间表示：

```
list[KnowledgeGraph]  →  GraphBuilder.build()  →  nx.DiGraph  →  AGE storage
```

### 6.2 去重规则

| 元素 | 唯一键 | 合并策略 |
|------|--------|---------|
| 节点 | `id`（标准名称） | 保留最长的 `name`、最详细的 `description` |
| 边 | `(source, target, relationship_name)` | 保留最先发现的，后续跳过 |

### 6.3 溯源

每个节点标注 `source_chunk_index`，支持回溯到原始切片的文本和文档。

## 7. AGE 存储 (Storage)

### 7.1 图模型

```sql
-- 初始化（仅一次）
SELECT * from ag_catalog.create_graph('chuma_kg');

-- Vertex 标签：Entity
-- Edge 标签：RELATION（带 relationship_name 属性区分类型）
```

### 7.2 写入流程

```
对每个节点 → CREATE (n:Entity {id, name, type, description})
对每条边 → MATCH (a),(b) CREATE (a)-[r:RELATION {name, description}]->(b)
```

### 7.3 新增配置项

```ini
# .env
AGE_HOST=10.16.75.254
AGE_PORT=5432
AGE_DB=chuma
AGE_USER=chuma
AGE_PASSWORD=chuma
AGE_GRAPH_NAME=chuma_kg
```

### 7.4 必要依赖

```
psycopg2-binary>=2.9
```

（AGE 使用 PostgreSQL 协议，通过 `psycopg2` 驱动）

## 8. Pipeline 编排

### 8.1 流程

```
KGPipeline.run(file_path)
  ├── Stage 1: OCR 解析
  │     OCRService.run_ocr_parse() → 读取 .md 内容
  ├── Stage 2: 切片
  │     MarkdownChunker.chunk() → list[DocumentChunk]
  ├── Stage 3: LLM 抽取（逐块）
  │     KGExtractor.extract_from_chunk() → list[KnowledgeGraph]
  ├── Stage 4: 图合并
  │     GraphBuilder.build() → nx.DiGraph
  └── Stage 5: AGE 持久化
        AgeStorage.write_graph() → PipelineResult
```

### 8.2 异步任务集成

通过 `@task_handler("kg_build")` 注册为 Redis 队列任务，与现有的 `worker.py` 架构一致。

### 8.3 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/kg/build` | 提交构建任务（异步） |
| GET | `/kg/build/status/{task_id}` | 查询任务状态 |
| GET | `/kg/graph/search?q=...` | 在图谱中搜索实体 |
| GET | `/kg/graph/visualize/{dataset_id}` | 导出图结构 JSON |

## 9. 异常处理

### 9.1 异常层级

```python
KGPipelineError           # 基类
├── OcrServiceError       # OCR 服务故障
├── LlmExtractionError    # LLM 解析格式错误
├── AgeConnectionError    # AGE 连接超时
└── InvalidGraphError     # 图数据校验失败
```

### 9.2 日志规范

每个阶段使用 `pipeline_span()` context manager 包裹，自动记录 `[KG] Starting phase: X` / `[KG] Completed phase: X`，异常时记录 `[KG] Phase failed: X` + traceback。

## 10. 配置清单

### 10.1 新增 Python 依赖

```
psycopg2-binary>=2.9      # AGE 驱动
networkx>=3.0              # 中间图表示
```

### 10.2 新增环境变量

```ini
AGE_HOST=10.16.75.254
AGE_PORT=5432
AGE_DB=chuma
AGE_USER=chuma
AGE_PASSWORD=chuma
AGE_GRAPH_NAME=chuma_kg
```

## 11. 对比 Cognee 的设计差异

| 维度 | Cognee | 本设计 | 理由 |
|------|--------|--------|------|
| 切片 | 纯文本句子级别 | Markdown 标题感知 | 教材有明确章节结构 |
| 实体类型 | 自由抽取 | 8 种预定义 CS 类型 | 保证学科内一致性 |
| 存储 | 三层（Rel + Graph + Vector） | 仅 AGE (Graph) | 需求聚焦，YAGNI |
| 中间图 | 自定义 DataPoint | NetworkX | 成熟稳定，工具链丰富 |
| LLM 框架 | LLMGateway / Instructor | chat() + Pydantic 后验 | 兼容 Qwen3.5-9B |

## 12. 未来扩展

- **向量层**：增加实体名嵌入到 ChromaDB，支持语义搜索
- **增量更新**：支持仅更新修改过的切片，避免全量重建
- **查询层**：参考 Cognee 的 `recall()`，实现 GraphRAG 问答
- **可视化**：导出 D3.js 交互式图谱（参考 Cognee `visualize_graph()`）
