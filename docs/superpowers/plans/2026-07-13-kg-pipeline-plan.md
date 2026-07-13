# 知识图谱自动构建 Pipeline 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个端到端的知识图谱构建 Pipeline，支持 PDF/文档 → OCR → Chunking → LLM 抽取 → AGE 持久化。

**Architecture:** 五个独立模块（Chunking、Extraction、GraphBuilder、Storage、Pipeline），由 Pipeline 类编排，通过异步任务（Redis 队列）触发。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, NetworkX, psycopg2-binary, Apache AGE (PostgreSQL extension), LLMClient (Qwen3.5-9B)

**已有的 OCR 服务：** `ai/app/ocr/service.py` 中的 `run_ocr_parse()` / `get_infer_result()`

## 全局约束

- 所有函数必须包含完整的 Python Type Hints
- LLM 调用统一通过 `ai/app/engines/llm/client.py` 的 `LLMClient`，默认使用 `quick_profile()`
- 配置从 `.env` 读取，使用 `pydantic-settings`
- git 提交仅在最终交付时进行
- 所有新代码放在 `ai/app/kg_pipeline/` 模块下

---

## 文件结构概览

```
# 新建文件
ai/app/kg_pipeline/
├── __init__.py               # 导出核心类
├── models.py                 # Pydantic 数据模型
├── chunking.py               # Markdown 文本切片
├── extraction.py             # LLM 实体/关系抽取
├── graph_builder.py          # NetworkX 内存图构建与去重
├── storage.py                # Apache AGE 持久化
├── pipeline.py               # Pipeline 编排调度
└── prompts/
    ├── __init__.py
    └── kg_extraction.txt     # LLM 抽取提示词

# 修改文件
ai/app/config.py              # 新增 AGE 配置项
ai/app/api/kg.py              # 实现 API 端点
ai/app/tasks/__init__.py      # 导入 kg_build 任务（自动发现）
ai/requirements.txt            # 新增依赖

# 新建测试文件
ai/tests/
├── test_models.py
├── test_chunking.py
├── test_extraction.py
├── test_graph_builder.py
├── test_storage.py
└── test_pipeline.py

# 配置文件
.env.example                  # 新增 AGE 配置项
```

---

### Task 1：数据类型定义 (models.py)

**Files:**
- Create: `ai/app/kg_pipeline/models.py`

**Interfaces:**
- Produces: `EntityType` (enum), `KGNode` (BaseModel), `KGEdge` (BaseModel), `KnowledgeGraph` (BaseModel), `DocumentChunk` (BaseModel), `PipelineResult` (BaseModel)

- [ ] **Step 1: Write models.py**

```python
"""知识图谱构建 Pipeline 的数据模型"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """预定义的计算机学科实体类型"""
    CONCEPT = "Concept"
    ALGORITHM = "Algorithm"
    DATA_STRUCTURE = "DataStructure"
    PROTOCOL = "Protocol"
    PRINCIPLE = "Principle"
    TERM = "Term"
    TECHNOLOGY = "Technology"
    MODEL = "Model"


class KGNode(BaseModel):
    """知识图谱节点 — 对应 AGE 中的一个 Vertex"""
    id: str
    name: str = ""
    type: EntityType
    description: str = ""
    source_chunk_index: Optional[int] = None

    def __init__(self, **data):
        if not data.get("name"):
            data["name"] = data.get("id", "")
        super().__init__(**data)


class KGEdge(BaseModel):
    """知识图谱边 — 对应 AGE 中的一条 Edge"""
    source_node_id: str
    target_node_id: str
    relationship_name: str
    description: Optional[str] = None


class KnowledgeGraph(BaseModel):
    """单个切片的知识图谱"""
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """文档切片"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    chunk_index: int = 0
    chunk_size: int = 0


class PipelineResult(BaseModel):
    """Pipeline 执行结果统计"""
    chunks: int = 0
    nodes: int = 0
    edges: int = 0
    status: str = "pending"
    error: Optional[str] = None
```

- [ ] **Step 2: Verify models**

```bash
cd ai && python -c "from app.kg_pipeline.models import EntityType, KGNode, KGEdge, KnowledgeGraph; print('models OK')"
```

Expected: `models OK`

---

### Task 2：配置与环境变量

**Files:**
- Modify: `ai/app/config.py`
- Modify: `.env.example`
- Create: `ai/app/kg_pipeline/__init__.py`

**Interfaces:**
- Produces: `settings.AGE_*` 配置属性，被 `storage.py` 消费

- [ ] **Step 1: Add AGE config to Settings**

在 `ai/app/config.py` 的 `Settings` 类中新增：

```python
# Apache AGE
AGE_HOST: str = "10.16.75.254"
AGE_PORT: int = 5432
AGE_DB: str = "chuma"
AGE_USER: str = "chuma"
AGE_PASSWORD: str = ""
AGE_GRAPH_NAME: str = "chuma_kg"
```

- [ ] **Step 2: Update `.env.example`**

```ini
# === Apache AGE ===
AGE_HOST=10.16.75.254
AGE_PORT=5432
AGE_DB=chuma
AGE_USER=chuma
AGE_PASSWORD=change-me
AGE_GRAPH_NAME=chuma_kg
```

- [ ] **Step 3: Create `__init__.py`**

```python
from app.kg_pipeline.models import KGNode, KGEdge, KnowledgeGraph, DocumentChunk, EntityType
from app.kg_pipeline.chunking import MarkdownChunker
from app.kg_pipeline.extraction import KGExtractor
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.storage import AgeStorage
from app.kg_pipeline.pipeline import KGPipeline, PipelineResult

__all__ = [
    "KGNode", "KGEdge", "KnowledgeGraph", "DocumentChunk", "EntityType",
    "MarkdownChunker", "KGExtractor", "GraphBuilder", "AgeStorage",
    "KGPipeline", "PipelineResult",
]
```

- [ ] **Step 4: Verify config loads**

```bash
cd ai && python -c "from app.config import settings; print(settings.AGE_HOST, settings.AGE_GRAPH_NAME)"
```

Expected: `10.16.75.254 chuma_kg`

---

### Task 3：Markdown 文本切片 (chunking.py)

**Files:**
- Create: `ai/app/kg_pipeline/chunking.py`
- Test (later): `ai/tests/test_chunking.py`

**Interfaces:**
- Consumes: `DocumentChunk` (from models.py)
- Produces: `MarkdownChunker.chunk(text: str) -> list[DocumentChunk]`

参考 Cognee 的 `chunk_by_paragraph` + `chunk_by_sentence` 策略，但适配 Markdown 标题结构。

- [ ] **Step 1: Write chunking.py**

```python
"""Markdown 感知的文本切片器

按标题分割 Markdown 文档，在每个 section 内部按句子粒度切分，
聚合为不超过 max_chunk_size 的块。不会跨越标题边界。
"""

import re
import uuid
from typing import Iterator

from app.kg_pipeline.models import DocumentChunk


def _split_by_heading(markdown_text: str) -> list[str]:
    """按 Markdown 标题分割文档

    支持 # ## ### 级别的标题，保留标题文本在 section 内容开头。
    """
    # 匹配行首的 # 标题
    heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    sections = []
    last_end = 0
    last_start = 0

    for match in heading_pattern.finditer(markdown_text):
        if last_start > 0:
            sections.append(markdown_text[last_start:match.start()].strip())
        last_start = match.start()

    # 最后一段
    if last_start < len(markdown_text):
        sections.append(markdown_text[last_start:].strip())

    # 如果没有标题，整篇作为一个 section
    if not sections:
        sections = [markdown_text.strip()]

    return [s for s in sections if s]


def _estimate_token_count(text: str) -> int:
    """估算文本的 token 数量（中英文混合，约 1.5 chars/token）"""
    return max(1, len(text) // 2)


def _chunk_section(section: str, max_chunk_size: int, base_index: int = 0) -> list[DocumentChunk]:
    """将一个 section 按句子切分为 chunks

    使用简单的句子边界（。！？\n\n）分割，聚合到 max_chunk_size。
    实现参考 Cognee 的 chunk_by_paragraph 策略。
    """
    if not section:
        return []

    chunks = []
    current_text = ""
    current_size = 0
    chunk_index = base_index

    # 按段落分割（双换行）
    paragraphs = re.split(r'\n\s*\n', section)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = _estimate_token_count(para)

        if current_size > 0 and current_size + para_size > max_chunk_size:
            # 保存当前块
            chunks.append(DocumentChunk(
                id=str(uuid.uuid4()),
                text=current_text.strip(),
                chunk_index=chunk_index,
                chunk_size=current_size,
            ))
            chunk_index += 1
            current_text = ""
            current_size = 0

        # 如果段落本身就超过 max_chunk_size，按句子切分
        if para_size > max_chunk_size:
            sentences = re.split(r'(?<=[。！？；;])\s*', para)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                sent_size = _estimate_token_count(sent)
                if current_size + sent_size > max_chunk_size and current_size > 0:
                    chunks.append(DocumentChunk(
                        id=str(uuid.uuid4()),
                        text=current_text.strip(),
                        chunk_index=chunk_index,
                        chunk_size=current_size,
                    ))
                    chunk_index += 1
                    current_text = ""
                    current_size = 0
                current_text += sent + " "
                current_size += sent_size
        else:
            current_text += para + "\n\n"
            current_size += para_size

    # 最后剩余文本
    if current_text.strip():
        chunks.append(DocumentChunk(
            id=str(uuid.uuid4()),
            text=current_text.strip(),
            chunk_index=chunk_index,
            chunk_size=current_size,
        ))

    return chunks


class MarkdownChunker:
    """Markdown 感知的文本切片器"""

    def __init__(self, max_chunk_size: int = 1024):
        self.max_chunk_size = max_chunk_size

    def chunk(self, markdown_text: str) -> list[DocumentChunk]:
        """对 Markdown 文本进行切片

        Args:
            markdown_text: 完整的 Markdown 文档内容

        Returns:
            按阅读顺序排列的 DocumentChunk 列表
        """
        if not markdown_text:
            return []

        sections = _split_by_heading(markdown_text)
        all_chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section in sections:
            section_chunks = _chunk_section(section, self.max_chunk_size, chunk_index)
            all_chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return all_chunks
```

- [ ] **Step 2: Quick smoke test**

```bash
cd ai && python -c "
from app.kg_pipeline.chunking import MarkdownChunker
chunker = MarkdownChunker(max_chunk_size=256)
text = '# TCP协议\n\nTCP是面向连接的协议。\n\n## 三次握手\n\n建立连接需要三次握手。\n第一次是SYN。'
chunks = chunker.chunk(text)
for c in chunks:
    print(f'[{c.chunk_index}] ({c.chunk_size} tokens): {c.text[:50]}...')
"
```

Expected: 2-3 chunks, each ≤256 tokens, no chunk crosses the `##` boundary.

---

### Task 4：LLM 抽取 (extraction.py + prompt)

**Files:**
- Create: `ai/app/kg_pipeline/extraction.py`
- Create: `ai/app/kg_pipeline/prompts/__init__.py`
- Create: `ai/app/kg_pipeline/prompts/kg_extraction.txt`

- [ ] **Step 1: Write the system prompt**

`prompts/kg_extraction.txt`:

```
You are a knowledge graph extraction expert specializing in computer science education. Your task is to extract structured knowledge points and their relationships from textbook content.

## Entity Types
Choose from these predefined types for each entity:

- Concept: Fundamental theoretical concepts, e.g., "virtual memory", "interrupt", "polymorphism"
- Algorithm: Specific algorithms, e.g., "quicksort", "banker's algorithm", "LRU replacement"
- DataStructure: Specific data structures, e.g., "hash table", "B+ tree", "stack"
- Protocol: Network protocols, e.g., "TCP", "HTTP", "IP"
- Principle: Theoretical principles or laws, e.g., "locality principle", "CAP theorem"
- Term: Specialized terminology, e.g., "thrashing", "deadlock", "starvation"
- Technology: Specific technologies or systems, e.g., "Linux", "relational database"
- Model: Theoretical or practical models, e.g., "OSI seven-layer model", "client-server model"

## Extraction Rules
1. Entity IDs must use the most standard and complete name in Chinese. Do NOT use numbers or UUIDs as IDs.
2. Every entity must have a type and description.
3. Relationship names must use snake_case in English, e.g.: contains, prerequisite_for, implements
4. Each edge description field must be a concrete single sentence that describes the relationship using the endpoint names.
   - GOOD: "TCP uses a three-way handshake to establish a connection, ensuring reliable data transmission."
   - BAD: "This edge describes a connection establishment mechanism."
5. Extract only entities and relationships explicitly mentioned in the text. Do NOT add outside knowledge.
6. If there are no meaningful relationships, you may return only nodes (empty edges list).

## Output Format
Respond with a valid JSON object containing "nodes" and "edges" arrays:
{
  "nodes": [
    {"id": "实体名称", "name": "实体名称", "type": "EntityType", "description": "实体描述"}
  ],
  "edges": [
    {"source_node_id": "源实体名称", "target_node_id": "目标实体名称", "relationship_name": "关系名", "description": "关系描述"}
  ]
}
```

- [ ] **Step 2: Write extraction.py**

```python
"""LLM 实体与关系抽取器"""

import json
import logging
import re
from typing import Optional

from app.kg_pipeline.models import DocumentChunk, KnowledgeGraph, KGNode, KGEdge
from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import ModelProfile, quick_profile


logger = logging.getLogger(__name__)

PROMPT_DIR = __file__.rsplit("/", 1)[0] + "/prompts"


def _load_prompt(filename: str = "kg_extraction.txt") -> str:
    """从 prompts 目录加载提示词文件"""
    import os
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_llm_json_response(raw: str) -> dict:
    """从 LLM 响应中提取 JSON

    处理 LLM 返回 markdown 包裹的 JSON 代码块：
    ```json\n{"nodes": ...}\n```
    或裸 JSON。
    """
    # 尝试提取 ```json ... ``` 代码块
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if code_block:
        raw = code_block.group(1).strip()

    # 尝试提取最外层的 {} 或 []
    brace_start = raw.find('{')
    if brace_start >= 0:
        raw = raw[brace_start:]

    return json.loads(raw)


class LlmExtractionError(Exception):
    """LLM 解析格式错误"""
    pass


class KGExtractor:
    """从文档切片中提取知识图谱"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        profile: Optional[ModelProfile] = None,
        custom_prompt: Optional[str] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.profile = profile or quick_profile()
        self.system_prompt = custom_prompt or _load_prompt()

    async def extract_from_chunk(self, chunk: DocumentChunk) -> KnowledgeGraph:
        """从单个切片提取知识图谱

        Args:
            chunk: 文档切片

        Returns:
            KnowledgeGraph 包含抽取的节点和边

        Raises:
            LlmExtractionError: LLM 返回格式无法解析
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": chunk.text},
        ]

        try:
            raw = await self.llm.chat(
                messages,
                temperature=0.1,
                profile=self.profile,
            )
        except Exception as e:
            raise LlmExtractionError(f"LLM call failed: {e}") from e

        try:
            data = _parse_llm_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {raw[:200]}")
            raise LlmExtractionError(f"JSON parse failed: {e}") from e

        # 用 Pydantic 校验结构
        try:
            nodes = [
                KGNode(
                    id=n.get("id", n.get("name", "")),
                    name=n.get("name", n.get("id", "")),
                    type=n["type"],
                    description=n.get("description", ""),
                    source_chunk_index=chunk.chunk_index,
                )
                for n in data.get("nodes", [])
                if n.get("id") or n.get("name")
            ]
            edges = [
                KGEdge(
                    source_node_id=e["source_node_id"],
                    target_node_id=e["target_node_id"],
                    relationship_name=e["relationship_name"],
                    description=e.get("description"),
                )
                for e in data.get("edges", [])
                if e.get("source_node_id") and e.get("target_node_id")
            ]
        except (KeyError, TypeError) as e:
            raise LlmExtractionError(f"Field validation failed: {e}") from e

        return KnowledgeGraph(nodes=nodes, edges=edges)
```

- [ ] **Step 3: Test prompt loads**

```bash
cd ai && python -c "from app.kg_pipeline.extraction import _load_prompt; p = _load_prompt(); print(f'Prompt loaded: {len(p)} chars')"
```

Expected: `Prompt loaded: ~2000 chars`

---

### Task 5：图构建去重 (graph_builder.py)

**Files:**
- Create: `ai/app/kg_pipeline/graph_builder.py`

- [ ] **Step 1: Write graph_builder.py**

```python
"""NetworkX 内存图构建与去重"""

import logging
from typing import Optional

import networkx as nx

from app.kg_pipeline.models import KnowledgeGraph, KGNode, KGEdge


logger = logging.getLogger(__name__)


class GraphBuilder:
    """合并多个切片的知识图谱为一张统一的内存图

    使用 NetworkX DiGraph 作为中间表示，
    在写入 AGE 前完成实体去重和边验证。
    """

    def build(
        self,
        chunk_graphs: list[KnowledgeGraph],
    ) -> nx.DiGraph:
        """合并多个 KnowledgeGraph 片段为统一图

        Args:
            chunk_graphs: 每个切片抽取的图片段

        Returns:
            NetworkX DiGraph，节点属性含 name/type/description，
            边属性含 relationship_name/description
        """
        G = nx.DiGraph()

        for kg in chunk_graphs:
            # 添加/合并节点
            for node in kg.nodes:
                if node.id in G:
                    existing = G.nodes[node.id]
                    # 保留更长的 name
                    if len(node.name) > len(existing.get("name", "")):
                        G.nodes[node.id]["name"] = node.name
                    # 保留更详细的 description
                    if len(node.description) > len(existing.get("description", "")):
                        G.nodes[node.id]["description"] = node.description
                else:
                    G.add_node(
                        node.id,
                        name=node.name,
                        type=node.type.value if hasattr(node.type, 'value') else node.type,
                        description=node.description,
                        source_chunk_index=node.source_chunk_index,
                    )

            # 添加边（去重）
            for edge in kg.edges:
                if edge.source_node_id not in G:
                    logger.warning(f"Edge source {edge.source_node_id} not in graph, skipping")
                    continue
                if edge.target_node_id not in G:
                    logger.warning(f"Edge target {edge.target_node_id} not in graph, skipping")
                    continue

                # 同一条边（相同 source + target + relationship）不再重复添加
                key = (edge.source_node_id, edge.target_node_id)
                if G.has_edge(*key):
                    existing_edge = G.edges[key]
                    if existing_edge.get("relationship_name") == edge.relationship_name:
                        continue

                G.add_edge(
                    edge.source_node_id,
                    edge.target_node_id,
                    relationship_name=edge.relationship_name,
                    description=edge.description,
                )

        return G
```

- [ ] **Step 2: Quick test**

```bash
cd ai && python -c "
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.models import KnowledgeGraph, KGNode, KGEdge, EntityType

builder = GraphBuilder()
kg1 = KnowledgeGraph(
    nodes=[KGNode(id='TCP', type=EntityType.PROTOCOL, description='传输控制协议')],
    edges=[]
)
kg2 = KnowledgeGraph(
    nodes=[KGNode(id='TCP', type=EntityType.PROTOCOL, description='可靠的传输层协议（补充）')],
    edges=[]
)
G = builder.build([kg1, kg2])
print(f'Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}')
print(f'TCP description: {G.nodes[\"TCP\"][\"description\"]}')
"
```

Expected: `Nodes: 1, Edges: 0`（去重成功，description 合并为更详细的版本）

---

### Task 6：Apache AGE 持久化 (storage.py)

**Files:**
- Create: `ai/app/kg_pipeline/storage.py`

- [ ] **Step 1: Write storage.py**

```python
"""Apache AGE 持久化适配器

通过 PostgreSQL 协议操作 AGE 扩展的 Cypher 接口。
AGE 图数据模型：
  - Vertex label: Entity
    - Properties: id (str), name (str), type (str), description (str)
  - Edge label: RELATION
    - Properties: relationship_name (str), description (str)
"""

import logging
from typing import Optional

import networkx as nx
import psycopg2
import psycopg2.extras

from app.config import settings
from app.kg_pipeline.models import PipelineResult


logger = logging.getLogger(__name__)


class AgeConnectionError(Exception):
    """AGE 数据库连接失败"""
    pass


def _build_dsn() -> str:
    """从 settings 构建 PostgreSQL DSN"""
    return (
        f"host={settings.AGE_HOST} "
        f"port={settings.AGE_PORT} "
        f"dbname={settings.AGE_DB} "
        f"user={settings.AGE_USER} "
        f"password={settings.AGE_PASSWORD}"
    )


class AgeStorage:
    """Apache AGE 持久化适配器"""

    def __init__(self, dsn: Optional[str] = None, graph_name: Optional[str] = None):
        self._dsn = dsn or _build_dsn()
        self._graph_name = graph_name or settings.AGE_GRAPH_NAME

    def _get_conn(self):
        """创建 AGE 数据库连接"""
        try:
            conn = psycopg2.connect(self._dsn)
            conn.set_session(autocommit=True)
            return conn
        except psycopg2.OperationalError as e:
            raise AgeConnectionError(f"Cannot connect to AGE: {e}") from e

    def initialize_graph(self) -> None:
        """初始化 AGE 图（幂等）

        如果图已存在则忽略。
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ag_catalog.create_graph(%s)", (self._graph_name,))
        except psycopg2.errors.DuplicateObject:
            logger.info(f"Graph '{self._graph_name}' already exists, skipping creation")
        except Exception as e:
            logger.warning(f"Graph initialization warning: {e}")
        finally:
            conn.close()

    def write_graph(self, graph: nx.DiGraph) -> int:
        """将 NetworkX 图写入 AGE

        Args:
            graph: NetworkX DiGraph

        Returns:
            写入的边数

        Raises:
            AgeConnectionError: 数据库连接失败
        """
        conn = self._get_conn()
        edge_count = 0

        try:
            with conn.cursor() as cur:
                # 设置 AGE 搜索路径
                cur.execute("SET search_path TO ag_catalog, public;")

                # 写入节点
                for node_id, attrs in graph.nodes(data=True):
                    name = attrs.get("name", node_id)
                    ntype = attrs.get("type", "Concept")
                    desc = attrs.get("description", "")

                    cypher = (
                        f"SELECT * FROM cypher('{self._graph_name}', $$ "
                        f"MERGE (n:Entity {{id: '{_escape(node_id)}'}}) "
                        f"SET n.name = '{_escape(name)}', "
                        f"n.type = '{_escape(ntype)}', "
                        f"n.description = '{_escape(desc)}' "
                        f"$$) AS (n ag_catalog.vertex);"
                    )
                    cur.execute(cypher)

                # 写入边
                for src, dst, attrs in graph.edges(data=True):
                    rel_name = attrs.get("relationship_name", "related_to")
                    desc = attrs.get("description", "")

                    cypher = (
                        f"SELECT * FROM cypher('{self._graph_name}', $$ "
                        f"MATCH (a:Entity {{id: '{_escape(src)}'}}) "
                        f"MATCH (b:Entity {{id: '{_escape(dst)}'}}) "
                        f"CREATE (a)-[r:RELATION {{"
                        f"relationship_name: '{_escape(rel_name)}', "
                        f"description: '{_escape(desc)}'"
                        f"}}]->(b) "
                        f"$$) AS (r ag_catalog.edge);"
                    )
                    cur.execute(cypher)
                    edge_count += 1

        except psycopg2.Error as e:
            logger.error(f"AGE write failed: {e}")
            raise AgeConnectionError(f"AGE write failed: {e}") from e
        finally:
            conn.close()

        return edge_count

    def clear_graph(self) -> None:
        """清除当前图的所有数据"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO ag_catalog, public;")
                cypher = (
                    f"SELECT * FROM cypher('{self._graph_name}', $$ "
                    f"MATCH (n) DETACH DELETE n "
                    f"$$) AS (n ag_catalog.vertex);"
                )
                cur.execute(cypher)
        except psycopg2.Error as e:
            logger.error(f"AGE clear failed: {e}")
            raise AgeConnectionError(f"AGE clear failed: {e}") from e
        finally:
            conn.close()


def _escape(value: str) -> str:
    """转义 Cypher 字符串中的单引号和反斜杠"""
    return value.replace("\\", "\\\\").replace("'", "\\'")
```

- [ ] **Step 2: Quick syntax check**

```bash
cd ai && python -c "from app.kg_pipeline.storage import AgeStorage, _build_dsn, _escape; print('storage module OK'); print(f'DSN: {_build_dsn()}')"
```

Expected: module loads, DSN printed (no actual connection attempt)

---

### Task 7：Pipeline 编排 (pipeline.py)

**Files:**
- Create: `ai/app/kg_pipeline/pipeline.py`
- Modify: `ai/tests/__init__.py` (empty, create if needed)

- [ ] **Step 1: Write pipeline.py**

```python
"""知识图谱构建 Pipeline — 端到端调度"""

import asyncio
import logging
import os
import tempfile
from typing import Optional

from app.kg_pipeline.models import DocumentChunk, KnowledgeGraph, PipelineResult
from app.kg_pipeline.chunking import MarkdownChunker
from app.kg_pipeline.extraction import KGExtractor, LlmExtractionError
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.storage import AgeStorage, AgeConnectionError
from app.ocr.service import (
    get_infer_result,
    get_output_parse_dir,
    run_ocr_parse as ocr_parse_files,
)
from app.ocr.schemas import OcrParseParams, StoredUpload


logger = logging.getLogger(__name__)

# AGE 图初始化标记
_age_initialized = False


class OcrServiceError(Exception):
    """OCR 服务故障"""
    pass


class KGPipeline:
    """知识图谱构建 Pipeline"""

    def __init__(
        self,
        chunker: Optional[MarkdownChunker] = None,
        extractor: Optional[KGExtractor] = None,
        graph_builder: Optional[GraphBuilder] = None,
        storage: Optional[AgeStorage] = None,
    ):
        self.chunker = chunker or MarkdownChunker()
        self.extractor = extractor or KGExtractor()
        self.graph_builder = graph_builder or GraphBuilder()
        self.storage = storage or AgeStorage()

    async def _parse_document(self, file_path: str, output_dir: str) -> str:
        """调用 OCR 服务解析文档为 Markdown

        Args:
            file_path: 文档路径（PDF/图片）
            output_dir: OCR 输出目录

        Returns:
            Markdown 内容字符串
        """
        filename = os.path.basename(file_path)
        stem = os.path.splitext(filename)[0]
        suffix = os.path.splitext(filename)[1].lstrip(".").lower()

        if suffix not in ("pdf", "jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"):
            raise OcrServiceError(f"Unsupported file type: .{suffix}")

        try:
            upload = StoredUpload(
                original_name=filename,
                stem=stem,
                path=file_path,
            )
            # 读取文件并调用 MinerU
            file_names = await ocr_parse_files(
                output_dir=output_dir,
                uploads=[upload],
                params=OcrParseParams(),
                server_url="",  # MinerU 自动处理
            )
        except Exception as e:
            raise OcrServiceError(f"OCR parsing failed: {e}") from e

        if not file_names:
            raise OcrServiceError("OCR returned no output files")

        pdf_name = file_names[0]
        parse_dir = get_output_parse_dir(output_dir, pdf_name)
        md_content = get_infer_result(".md", pdf_name, parse_dir)

        if md_content is None:
            raise OcrServiceError(f"Markdown result not found for {pdf_name}")

        return md_content

    async def _extract_all_chunks(
        self, chunks: list[DocumentChunk]
    ) -> list[KnowledgeGraph]:
        """逐块进行 LLM 抽取（顺序执行，LLM 调用不可并行）"""
        chunk_graphs: list[KnowledgeGraph] = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            logger.info(f"[KG] Extracting chunk {i + 1}/{total}")
            kg = await self.extractor.extract_from_chunk(chunk)
            chunk_graphs.append(kg)

        return chunk_graphs

    async def run_from_markdown(self, markdown_text: str) -> PipelineResult:
        """从 Markdown 文本直接构建知识图谱（跳过 OCR）

        Args:
            markdown_text: Markdown 格式的文档内容

        Returns:
            PipelineResult 执行统计
        """
        logger.info("[KG] Phase: Chunking")
        chunks = self.chunker.chunk(markdown_text)
        logger.info(f"[KG] Generated {len(chunks)} chunks")

        logger.info("[KG] Phase: LLM Extraction")
        chunk_graphs = await self._extract_all_chunks(chunks)

        # 统计
        total_nodes = sum(len(kg.nodes) for kg in chunk_graphs)
        total_edges = sum(len(kg.edges) for kg in chunk_graphs)
        logger.info(f"[KG] Extracted {total_nodes} nodes, {total_edges} edges from LLM")

        logger.info("[KG] Phase: Graph Building")
        graph = self.graph_builder.build(chunk_graphs)
        logger.info(f"[KG] Merged graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

        logger.info("[KG] Phase: AGE Storage")
        global _age_initialized
        if not _age_initialized:
            self.storage.initialize_graph()
            _age_initialized = True

        edge_count = self.storage.write_graph(graph)
        logger.info(f"[KG] Written {edge_count} edges to AGE")

        return PipelineResult(
            chunks=len(chunks),
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
            status="completed",
        )

    async def run_from_file(self, file_path: str) -> PipelineResult:
        """从原始文档文件构建知识图谱（PDF → OCR → KG）

        Args:
            file_path: 原始文档路径

        Returns:
            PipelineResult 执行统计
        """
        logger.info(f"[KG] Starting pipeline for: {file_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                logger.info("[KG] Phase: OCR Parsing")
                md_content = await self._parse_document(file_path, tmpdir)
                logger.info(f"[KG] OCR completed, Markdown length: {len(md_content)} chars")
            except OcrServiceError as e:
                logger.error(f"[KG] OCR failed: {e}")
                return PipelineResult(status="failed", error=str(e))

            return await self.run_from_markdown(md_content)
```

- [ ] **Step 2: Verify module imports**

```bash
cd ai && python -c "from app.kg_pipeline.pipeline import KGPipeline; print('pipeline OK')"
```

Expected: `pipeline OK`（依赖的 psycopg2 尚未安装时会有 ImportError，避免 - 这是 Task 8 处理）

---

### Task 8：安装依赖 + 配置加载验证

**Files:**
- Modify: `ai/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

```
# === 知识图谱构建 Pipeline ===
networkx>=3.0
psycopg2-binary>=2.9
```

加到 `ai/requirements.txt` 末尾。

- [ ] **Step 2: Install**

```bash
cd ai
pip install networkx psycopg2-binary
```

- [ ] **Step 3: Verify all imports**

```bash
cd ai && python -c "
from app.kg_pipeline.models import EntityType, KGNode, KGEdge, KnowledgeGraph, DocumentChunk
from app.kg_pipeline.chunking import MarkdownChunker
from app.kg_pipeline.extraction import KGExtractor
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.storage import AgeStorage
from app.kg_pipeline.pipeline import KGPipeline
print('All imports OK')
"
```

Expected: `All imports OK`

---

### Task 9：API 层 + 异步任务集成

**Files:**
- Modify: `ai/app/api/kg.py`
- Modify: `ai/app/tasks/__init__.py`（或新建 `ai/app/tasks/kg_build.py`）
- Create: `ai/tests/test_api_kg.py`

- [ ] **Step 1: Create async task handler**

`ai/app/tasks/kg_build.py`:

```python
"""知识图谱构建异步任务 — 由 Redis 队列触发"""

import json
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.kg_pipeline.pipeline import KGPipeline
from app.tasks.registry import task_handler


logger = logging.getLogger(__name__)


@task_handler("kg_build")
async def run_kg_build(task_data: dict):
    """执行知识图谱构建任务

    task_data 格式:
    {
        "task_id": "uuid",
        "file_path": "/path/to/document.pdf",
        "output_key": "kg:result:{task_id}"
    }
    """
    task_id = task_data.get("task_id", "unknown")
    file_path = task_data["file_path"]
    output_key = task_data.get("output_key", f"kg:result:{task_id}")

    logger.info(f"[KGBuild] Task {task_id}: building KG from {file_path}")

    pipeline = KGPipeline()
    result = await pipeline.run_from_file(file_path)

    # 结果写回 Redis
    r = aioredis.from_url(settings.REDIS_URL)
    await r.set(output_key, result.model_dump_json(), ex=86400)

    logger.info(f"[KGBuild] Task {task_id}: {result.status}")
```

- [ ] **Step 2: Implement API endpoints**

`ai/app/api/kg.py`:

```python
"""知识图谱管理路由"""

import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Body, HTTPException

from app.config import settings
from app.kg_pipeline.models import PipelineResult
from app.ocr.schemas import TaskSubmitResponse


router = APIRouter()


@router.post("/build", response_model=TaskSubmitResponse)
async def start_kg_build(file_path: str = Body(..., embed=True)):
    """提交知识图谱构建任务（异步）

    文件路径为远程服务器上的已有文件路径。
    """
    task_id = str(uuid.uuid4())

    r = aioredis.from_url(settings.REDIS_URL)
    await r.lpush("chuma:tasks", json.dumps({
        "type": "kg_build",
        "task_id": task_id,
        "file_path": file_path,
        "output_key": f"kg:result:{task_id}",
    }))

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/kg/build/status/{task_id}",
        result_url=f"/kg/build/result/{task_id}",
    )


@router.get("/build/status/{task_id}")
async def get_build_status(task_id: str):
    """查询构建任务状态"""
    r = aioredis.from_url(settings.REDIS_URL)
    result = await r.get(f"kg:result:{task_id}")
    if result is None:
        # 检查任务是否还在队列中
        return {"task_id": task_id, "status": "processing"}
    return json.loads(result)


@router.get("/build/result/{task_id}")
async def get_build_result(task_id: str):
    """获取构建结果"""
    r = aioredis.from_url(settings.REDIS_URL)
    result = await r.get(f"kg:result:{task_id}")
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return PipelineResult.model_validate_json(result)
```

- [ ] **Step 3: Verify API module imports**

```bash
cd ai && python -c "from app.api.kg import router; print('kg API router OK')"
```

Expected: `kg API router OK`

---

### Task 10：集成测试

- [ ] **Step 1: Run unit test for chunking**

```bash
cd ai && python -c "
from app.kg_pipeline.chunking import MarkdownChunker

chunker = MarkdownChunker(max_chunk_size=256)
text = '''# 第一章 数据结构概述

数据结构是计算机存储、组织数据的方式。

## 1.1 基本概念

数据(Data)是信息的载体。

## 1.2 算法

算法(Algorithm)是解决问题的步骤描述。
'''
chunks = chunker.chunk(text)
print(f'Total chunks: {len(chunks)}')
assert len(chunks) >= 2, 'Should produce multiple chunks'
for c in chunks:
    print(f'  Chunk [{c.chunk_index}]: {len(c.text)} chars, {c.chunk_size} tokens')
print('Chunking test PASSED')
"
```

- [ ] **Step 2: Run unit test for graph_builder**

```bash
cd ai && python -c "
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.models import KnowledgeGraph, KGNode, KGEdge, EntityType

builder = GraphBuilder()

# 两个切片，有重叠节点
kg1 = KnowledgeGraph(
    nodes=[
        KGNode(id='TCP', type=EntityType.PROTOCOL, description='传输控制协议'),
        KGNode(id='IP', type=EntityType.PROTOCOL, description='网际协议'),
    ],
    edges=[
        KGEdge(source_node_id='TCP', target_node_id='IP', relationship_name='depends_on', description='TCP 依赖 IP 协议传输数据'),
    ]
)
kg2 = KnowledgeGraph(
    nodes=[
        KGNode(id='TCP', type=EntityType.PROTOCOL, description='可靠的传输层协议'),
        KGNode(id='UDP', type=EntityType.PROTOCOL, description='用户数据报协议'),
    ],
    edges=[
        KGEdge(source_node_id='TCP', target_node_id='UDP', relationship_name='contrasts_with', description='TCP 和 UDP 是传输层两种主要协议'),
    ]
)

G = builder.build([kg1, kg2])
assert G.number_of_nodes() == 3, f'Expected 3 nodes, got {G.number_of_nodes()}'
assert G.number_of_edges() == 2, f'Expected 2 edges, got {G.number_of_edges()}'
# TCP 应该保留更长的 description
assert len(G.nodes['TCP']['description']) > 10
print(f'Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
print('Graph builder test PASSED')
"
```

- [ ] **Step 3: Run end-to-end dry-run (markdown → KG, skip OCR + AGE)**

```bash
cd ai && python -c "
import asyncio
from app.kg_pipeline.pipeline import KGPipeline
from app.kg_pipeline.storage import AgeStorage

async def test():
    # 使用不会实际连接 AGE 的 pipeline
    pipeline = KGPipeline()
    
    md = '''# TCP/IP 协议栈

TCP/IP 协议栈是互联网的基础通信协议。

## 应用层

应用层提供网络应用服务，如 HTTP、FTP。

## 传输层

传输层提供端到端通信，主要协议有 TCP 和 UDP。
TCP 是面向连接的可靠传输协议。
UDP 是无连接的不可靠传输协议。

## 网际层

网际层核心协议是 IP，负责数据包的路由和转发。
'''
    
    result = await pipeline.run_from_markdown(md)
    print(f'Result: {result.model_dump_json(indent=2)}')
    
print('Dry-run test completed')

asyncio.run(test())
" 2>&1 | head -40
```
