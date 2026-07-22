"""教材多层知识图谱构建测试"""

import pytest

from app.kg_pipeline.models import EntityType, DocumentChunk, KGNode, KGEdge, KnowledgeGraph


class TestEntityType:
    def test_chapter_type_exists(self):
        """EntityType 应包含 Chapter 类型"""
        assert hasattr(EntityType, "CHAPTER")
        assert EntityType.CHAPTER.value == "Chapter"

    def test_entity_types_count(self):
        """EntityType 应有 9 种类型（原有 8 + 新增 Chapter）"""
        assert len(EntityType) == 9


class TestDocumentChunk:
    def test_heading_path_default_empty(self):
        """heading_path 默认为空列表"""
        chunk = DocumentChunk(text="hello")
        assert chunk.heading_path == []

    def test_heading_levels_default_empty(self):
        """heading_levels 默认为空列表"""
        chunk = DocumentChunk(text="hello")
        assert chunk.heading_levels == []

    def test_chunk_with_heading_metadata(self):
        """chunk 可携带标题路径和级别"""
        chunk = DocumentChunk(
            text="栈是后进先出的数据结构",
            heading_path=["第3章 栈和队列", "3.1 栈"],
            heading_levels=[2, 3],
        )
        assert chunk.heading_path == ["第3章 栈和队列", "3.1 栈"]
        assert chunk.heading_levels == [2, 3]


from app.kg_pipeline.chunking import MarkdownChunker, _scan_heading_levels, _map_heading_levels


class TestScanHeadingLevels:
    def test_multiple_levels(self):
        md = "# Ch1\n\n## 1.1\n\n### 1.1.1\n\n## 1.2\n"
        levels = _scan_heading_levels(md)
        assert levels == [1, 2, 3]

    def test_single_level(self):
        md = "## Ch1\n\n## Ch2\n"
        levels = _scan_heading_levels(md)
        assert levels == [2]

    def test_no_headings(self):
        md = "Just plain text.\n"
        levels = _scan_heading_levels(md)
        assert levels == []

    def test_out_of_order_levels(self):
        md = "### 1.1.1\n\n# Ch1\n\n## 1.1\n"
        levels = _scan_heading_levels(md)
        assert levels == [1, 2, 3]


class TestMapHeadingLevels:
    def test_two_levels(self):
        mapping = _map_heading_levels([2, 3])
        assert mapping[2] == 1  # ## → 第1层（章）
        assert mapping[3] == 2  # ### → 第2层（知识点）

    def test_three_levels(self):
        mapping = _map_heading_levels([1, 2, 3])
        assert mapping[1] == 1  # # → 第1层
        assert mapping[2] == 2  # ## → 第2层
        assert mapping[3] == 2  # ### → 第2层（第3种归入第2层）

    def test_single_level(self):
        mapping = _map_heading_levels([2])
        assert mapping[2] == 1  # 唯一级别映射为第1层

    def test_four_levels(self):
        mapping = _map_heading_levels([1, 2, 3, 4])
        assert mapping[1] == 1
        assert mapping[2] == 2
        assert mapping[3] == 2
        assert mapping[4] == 2


class TestChunkerHeadingPath:
    def test_chunks_have_heading_path(self):
        md = "## 第3章 栈和队列\n\n栈是后进先出的数据结构。\n\n### 3.1 栈\n\n顺序栈和链栈。\n"
        chunker = MarkdownChunker(max_chunk_size=1024)
        chunks = chunker.chunk(md)
        assert len(chunks) >= 2
        first = [c for c in chunks if "第3章" in c.text][0]
        assert "第3章 栈和队列" in first.heading_path
        second = [c for c in chunks if "3.1 栈" in c.text][0]
        assert second.heading_path == ["第3章 栈和队列", "3.1 栈"]
        assert second.heading_levels == [2, 3]

    def test_no_heading_chunk_has_empty_path(self):
        md = "这是一段没有标题的文本。\n"
        chunker = MarkdownChunker(max_chunk_size=1024)
        chunks = chunker.chunk(md)
        assert len(chunks) == 1
        assert chunks[0].heading_path == []
        assert chunks[0].heading_levels == []

    def test_deep_heading_inherits_ancestors(self):
        md = "# 第1章\n\n## 1.1\n\n### 1.1.1\n\n详细内容。\n"
        chunker = MarkdownChunker(max_chunk_size=1024)
        chunks = chunker.chunk(md)
        deep_chunks = [c for c in chunks if "1.1.1" in c.heading_path]
        assert len(deep_chunks) >= 1
        deep = deep_chunks[0]
        assert "第1章" in deep.heading_path
        assert "1.1" in deep.heading_path
        assert "1.1.1" in deep.heading_path


from app.kg_pipeline.chapter_builder import ChapterBuilder


class TestChapterBuilder:
    def test_basic_chapter_generation(self):
        """从 chunks 的 heading_path 生成章节节点和 contains 边"""
        chunks = [
            DocumentChunk(
                text="内容1",
                heading_path=["第3章 栈和队列", "3.1 栈"],
                heading_levels=[2, 3],
            ),
            DocumentChunk(
                text="内容2",
                heading_path=["第3章 栈和队列", "3.2 队列"],
                heading_levels=[2, 3],
            ),
        ]
        builder = ChapterBuilder()
        kg = builder.build(chunks)

        # 应有 3 个章节节点
        node_ids = [n.id for n in kg.nodes]
        assert "第3章 栈和队列" in node_ids
        assert "3.1 栈" in node_ids
        assert "3.2 队列" in node_ids

        # 所有节点类型都是 Chapter
        for node in kg.nodes:
            assert node.type == EntityType.CHAPTER

        # 应有 2 条 contains 边：第3章→3.1, 第3章→3.2
        contains_edges = [e for e in kg.edges if e.relationship_name == "包含"]
        assert len(contains_edges) == 2

    def test_no_duplicate_nodes(self):
        """相同标题不应生成重复节点"""
        chunks = [
            DocumentChunk(text="内容1", heading_path=["第1章", "1.1"]),
            DocumentChunk(text="内容2", heading_path=["第1章", "1.1"]),  # 重复路径
        ]
        builder = ChapterBuilder()
        kg = builder.build(chunks)
        node_ids = [n.id for n in kg.nodes]
        assert node_ids.count("第1章") == 1
        assert node_ids.count("1.1") == 1

    def test_no_duplicate_edges(self):
        """相同 contains 边不应重复"""
        chunks = [
            DocumentChunk(text="内容1", heading_path=["第1章", "1.1"]),
            DocumentChunk(text="内容2", heading_path=["第1章", "1.1"]),
        ]
        builder = ChapterBuilder()
        kg = builder.build(chunks)
        contains_edges = [e for e in kg.edges if e.relationship_name == "包含"]
        # 第1章→1.1 只应出现一次
        assert len(contains_edges) == 1

    def test_empty_chunks(self):
        """空 chunks 返回空 KnowledgeGraph"""
        builder = ChapterBuilder()
        kg = builder.build([])
        assert len(kg.nodes) == 0
        assert len(kg.edges) == 0

    def test_chunks_without_headings(self):
        """没有 heading_path 的 chunks 返回空 KnowledgeGraph"""
        chunks = [DocumentChunk(text="内容")]
        builder = ChapterBuilder()
        kg = builder.build(chunks)
        assert len(kg.nodes) == 0
        assert len(kg.edges) == 0

    def test_multi_level_heading_path(self):
        """heading_path 中相邻元素形成 contains 边"""
        chunks = [
            DocumentChunk(
                text="内容",
                heading_path=["第1章 绪论", "1.1 数据结构", "1.1.1 基本概念"],
                heading_levels=[1, 2, 3],
            ),
        ]
        builder = ChapterBuilder()
        kg = builder.build(chunks)

        # 3 个章节节点
        assert len(kg.nodes) == 3

        # 2 条 contains 边：第1章→1.1, 1.1→1.1.1
        contains_edges = [e for e in kg.edges if e.relationship_name == "包含"]
        assert len(contains_edges) == 2

        edge_pairs = {(e.source_node_id, e.target_node_id) for e in contains_edges}
        assert ("第1章 绪论", "1.1 数据结构") in edge_pairs
        assert ("1.1 数据结构", "1.1.1 基本概念") in edge_pairs


from app.kg_pipeline.extraction import KGExtractor, _build_chapter_context


class TestChapterContext:
    def test_build_chapter_context_with_path(self):
        """有 heading_path 时生成章节上下文"""
        chunk = DocumentChunk(
            text="栈是后进先出的数据结构",
            heading_path=["第3章 栈和队列", "3.1 栈"],
        )
        context = _build_chapter_context(chunk)
        assert "第3章 栈和队列" in context
        assert "3.1 栈" in context
        assert "不要提取章节标题" in context

    def test_build_chapter_context_without_path(self):
        """无 heading_path 时返回空字符串"""
        chunk = DocumentChunk(text="普通文本")
        context = _build_chapter_context(chunk)
        assert context == ""

    def test_prompt_contains_no_chapter_title_rule(self):
        """系统 prompt 中应包含禁止提取章节标题的规则"""
        from app.kg_pipeline.extraction import _load_prompt
        prompt = _load_prompt()
        assert "禁止提取章节标题" in prompt or "Do not extract chapter or section titles" in prompt


from app.kg_pipeline.graph_builder import GraphBuilder


class TestGraphBuilderChapterMount:
    def test_knowledge_points_auto_mount_to_chapter(self):
        """知识点自动挂载到所属章节的叶节点"""
        builder = GraphBuilder()

        # 章节图
        chapter_graph = KnowledgeGraph(
            nodes=[
                KGNode(id="第3章 栈和队列", name="第3章 栈和队列", type=EntityType.CHAPTER),
                KGNode(id="3.1 栈", name="3.1 栈", type=EntityType.CHAPTER),
            ],
            edges=[
                KGEdge(source_node_id="第3章 栈和队列", target_node_id="3.1 栈", relationship_name="包含"),
            ],
        )

        # 知识点图（LLM 抽取结果）
        chunk_graphs = [
            KnowledgeGraph(
                nodes=[
                    KGNode(id="顺序栈", name="顺序栈", type=EntityType.DATA_STRUCTURE, description="用数组实现的栈", source_chunk_index=0),
                    KGNode(id="链栈", name="链栈", type=EntityType.DATA_STRUCTURE, description="用链表实现的栈", source_chunk_index=0),
                ],
                edges=[
                    KGEdge(source_node_id="顺序栈", target_node_id="链栈", relationship_name="对比"),
                ],
            ),
        ]

        # chunk 信息（用于自动挂载）
        chunks = [
            DocumentChunk(
                text="栈的实现...",
                heading_path=["第3章 栈和队列", "3.1 栈"],
                heading_levels=[2, 3],
                chunk_index=0,
            ),
        ]

        G = builder.build(
            chunk_graphs=chunk_graphs,
            chapter_graph=chapter_graph,
            chunks=chunks,
        )

        # 应有 4 个节点：2 章节 + 2 知识点
        assert G.number_of_nodes() == 4

        # 知识点应挂载到叶章节 "3.1 栈"
        assert G.has_edge("3.1 栈", "顺序栈")
        assert G.has_edge("3.1 栈", "链栈")

        # 挂载边的 relationship_name 应为 "包含"
        mount_edge = G.edges["3.1 栈", "链栈"]
        assert mount_edge["relationship_name"] == "包含"

    def test_no_chunks_no_auto_mount(self):
        """不传 chunks 时不自动挂载（向后兼容）"""
        builder = GraphBuilder()
        chunk_graphs = [
            KnowledgeGraph(
                nodes=[KGNode(id="TCP", name="TCP", type=EntityType.PROTOCOL)],
                edges=[],
            ),
        ]
        G = builder.build(chunk_graphs=chunk_graphs)
        assert G.number_of_nodes() == 1
        assert G.number_of_edges() == 0

    def test_chapter_nodes_merged_with_knowledge_points(self):
        """章节节点和知识点节点应合并到同一张图"""
        builder = GraphBuilder()

        chapter_graph = KnowledgeGraph(
            nodes=[
                KGNode(id="第1章", name="第1章", type=EntityType.CHAPTER),
            ],
            edges=[],
        )

        chunk_graphs = [
            KnowledgeGraph(
                nodes=[
                    KGNode(id="算法", name="算法", type=EntityType.CONCEPT, source_chunk_index=0),
                ],
                edges=[],
            ),
        ]

        chunks = [
            DocumentChunk(text="内容", heading_path=["第1章"], chunk_index=0),
        ]

        G = builder.build(
            chunk_graphs=chunk_graphs,
            chapter_graph=chapter_graph,
            chunks=chunks,
        )

        # 应有 2 个节点：1 章节 + 1 知识点
        assert G.number_of_nodes() == 2
        # 知识点应挂载到 "第1章"
        assert G.has_edge("第1章", "算法")


import networkx as nx

from app.kg_pipeline.cross_chapter import CrossChapterExtractor, _build_chapter_pairs, _build_cross_chapter_user_message


class TestChapterPairs:
    def test_basic_pair_generation(self):
        """生成去重的章节对"""
        chapters = ["第1章", "第2章", "第3章"]
        pairs = _build_chapter_pairs(chapters)
        # 应有 C(3,2)=3 对
        assert len(pairs) == 3
        # 每对应该有序（小索引在前）
        for a, b in pairs:
            assert chapters.index(a) < chapters.index(b)

    def test_two_chapters(self):
        chapters = ["第1章", "第2章"]
        pairs = _build_chapter_pairs(chapters)
        assert len(pairs) == 1
        assert pairs[0] == ("第1章", "第2章")

    def test_single_chapter(self):
        chapters = ["第1章"]
        pairs = _build_chapter_pairs(chapters)
        assert len(pairs) == 0

    def test_max_distance_filter(self):
        """超过最大距离的章节对应被过滤"""
        chapters = ["第1章", "第2章", "第3章", "第5章"]
        pairs = _build_chapter_pairs(chapters, max_distance=2)
        # 第1章和第5章距离为3，应被过滤
        for a, b in pairs:
            idx_a = chapters.index(a)
            idx_b = chapters.index(b)
            assert abs(idx_b - idx_a) <= 2

    def test_no_self_pairs(self):
        chapters = ["第1章", "第2章"]
        pairs = _build_chapter_pairs(chapters)
        for a, b in pairs:
            assert a != b


class TestCrossChapterPrompt:
    def test_prompt_structure(self):
        """跨章节 prompt 应包含两个章节和知识点"""
        user_msg = _build_cross_chapter_user_message(
            chapter_a="第3章 栈和队列",
            points_a=["栈", "队列", "顺序栈"],
            chapter_b="第4章 串",
            points_b=["串", "模式匹配", "KMP算法"],
        )
        assert "第3章 栈和队列" in user_msg
        assert "第4章 串" in user_msg
        assert "栈" in user_msg
        assert "KMP算法" in user_msg


class TestCrossChapterExtractor:
    def test_extractor_init(self):
        """CrossChapterExtractor 应可实例化"""
        extractor = CrossChapterExtractor(enable=True)
        assert extractor.enable is True

    @pytest.mark.asyncio
    async def test_extractor_disabled(self):
        """禁用时 extract 返回空列表"""
        extractor = CrossChapterExtractor(enable=False)
        G = nx.DiGraph()
        result = await extractor.extract(G)
        assert result == []


from unittest.mock import AsyncMock, MagicMock, patch

# Mock mineru and OCR modules (not available in local dev environment)
import sys
for _mod in ["mineru", "mineru.cli", "mineru.cli.common", "mineru.cli.doc_analyze",
             "mineru.model", "mineru.model.doc_analyze", "mineru.pipeline",
             "app.ocr.service", "app.ocr.schemas"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.kg_pipeline.pipeline import KGPipeline


class TestPipelineIntegration:
    def test_pipeline_has_chapter_builder(self):
        """KGPipeline 应包含 chapter_builder 属性"""
        pipeline = KGPipeline()
        assert hasattr(pipeline, "chapter_builder")
        assert isinstance(pipeline.chapter_builder, ChapterBuilder)

    def test_pipeline_has_cross_chapter_extractor(self):
        """KGPipeline 应包含 cross_chapter_extractor 属性"""
        pipeline = KGPipeline()
        assert hasattr(pipeline, "cross_chapter_extractor")
        assert isinstance(pipeline.cross_chapter_extractor, CrossChapterExtractor)

    def test_pipeline_enable_cross_chapter_param(self):
        """enable_cross_chapter 参数应传递给 CrossChapterExtractor"""
        pipeline = KGPipeline(enable_cross_chapter=False)
        assert pipeline.cross_chapter_extractor.enable is False

        pipeline = KGPipeline(enable_cross_chapter=True)
        assert pipeline.cross_chapter_extractor.enable is True

    @pytest.mark.asyncio
    async def test_pipeline_markdown_flow_with_chapters(self):
        """Pipeline 应生成章节节点并挂载知识点"""
        # Mock extractor 和 storage
        mock_extractor = AsyncMock()
        mock_extractor.extract_from_chunk.return_value = KnowledgeGraph(
            nodes=[
                KGNode(id="顺序栈", name="顺序栈", type=EntityType.DATA_STRUCTURE, description="用数组实现的栈", source_chunk_index=0),
            ],
            edges=[],
        )

        mock_storage = MagicMock()
        mock_storage.initialize_graph.return_value = None
        mock_storage.write_graph.return_value = 5

        # Mock cross_chapter_extractor
        mock_cross = AsyncMock()
        mock_cross.extract.return_value = []

        pipeline = KGPipeline(
            extractor=mock_extractor,
            storage=mock_storage,
            enable_cross_chapter=True,
        )
        pipeline.cross_chapter_extractor = mock_cross

        md = "## 第3章 栈和队列\n\n栈是后进先出的数据结构。\n\n### 3.1 栈\n\n顺序栈和链栈。\n"
        result = await pipeline.run_from_markdown(md)

        assert result.status == "completed"
        # 应有章节节点
        assert result.nodes >= 2  # 至少 2 个章节 + 知识点
