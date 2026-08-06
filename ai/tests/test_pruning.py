"""知识图谱剪枝守卫单元测试"""

import pytest
import networkx as nx

from app.kg_pipeline.models import EntityType, KGNode, KGEdge, KnowledgeGraph3D
from app.kg_pipeline.pruning import (
    CORE_TYPES,
    MAX_GLOBAL_NODES,
    filter_chunk_graph,
    is_valid_node_name,
    normalize_name,
    normalize_relationship,
    prune_global_graph,
)


class TestNormalizeName:
    def test_strip_whitespace(self):
        assert normalize_name("  栈  ") == "栈"

    def test_fullwidth_parens_to_halfwidth(self):
        assert normalize_name("栈（Stack）") == "栈(Stack)"

    def test_collapse_spaces(self):
        assert normalize_name("B+  树") == "B+ 树"

    def test_trailing_numbering(self):
        assert normalize_name("排序算法1.") == "排序算法"
        assert normalize_name("快速排序 1、") == "快速排序"

    def test_wrapped_paren_numbering(self):
        assert normalize_name("排序算法（1）") == "排序算法"
        assert normalize_name("排序算法(1)") == "排序算法"

    def test_keeps_bare_trailing_digits(self):
        # 裸尾随数字是合法名称的一部分（协议/技术/版本号），不应剥离
        assert normalize_name("IPv6") == "IPv6"
        assert normalize_name("x86") == "x86"
        assert normalize_name("HTTP/2") == "HTTP/2"
        assert normalize_name("HTTP/1.1") == "HTTP/1.1"  # "." 在串中，非尾部编号

    def test_unchanged(self):
        assert normalize_name("B+树") == "B+树"


class TestIsValidNodeName:
    def test_empty(self):
        assert is_valid_node_name("") is False

    def test_pure_symbols_or_digits(self):
        assert is_valid_node_name("!!!") is False
        assert is_valid_node_name("123") is False

    def test_generic_word(self):
        assert is_valid_node_name("概念") is False
        assert is_valid_node_name("特点") is False

    def test_valid(self):
        assert is_valid_node_name("栈") is True
        assert is_valid_node_name("顺序栈") is True
        assert is_valid_node_name("TCP") is True


class TestNormalizeRelationship:
    def test_canonical_passthrough(self):
        assert normalize_relationship("依赖") == "依赖"
        assert normalize_relationship("包含") == "包含"

    def test_synonym_mapped(self):
        assert normalize_relationship("使用到") == "使用"
        assert normalize_relationship("包括") == "包含"

    def test_unknown_returns_none(self):
        assert normalize_relationship("对比") is None
        assert normalize_relationship("") is None
        assert normalize_relationship(None) is None


class TestFilterChunkGraph:
    def _kg(self) -> KnowledgeGraph3D:
        # "Function"/"Operation" 是未知类型，经 _missing_ 降级为 TERM
        return KnowledgeGraph3D(
            nodes=[
                KGNode(id="printf", name="printf", type="Function", description="输出函数"),
                KGNode(id="栈（Stack）", name="栈（Stack）", type=EntityType.DATA_STRUCTURE, description="后进先出"),
                KGNode(id="入栈", name="入栈", type="Operation", description="入栈操作"),
            ],
            edges=[
                KGEdge(source_node_id="栈（Stack）", target_node_id="入栈", relationship_name="对比"),
                KGEdge(source_node_id="栈（Stack）", target_node_id="栈（Stack）", relationship_name="依赖"),
            ],
        )

    def test_drops_non_core_types(self):
        kg = filter_chunk_graph(self._kg())
        assert {n.id for n in kg.nodes} == {"栈(Stack)"}

    def test_normalizes_ids_and_names(self):
        kg = filter_chunk_graph(self._kg())
        node = kg.nodes[0]
        assert node.id == "栈(Stack)"
        assert node.name == "栈(Stack)"

    def test_drops_edges_to_removed_nodes_and_self_loops(self):
        kg = filter_chunk_graph(self._kg())
        assert kg.edges == []

    def test_drops_non_vocabulary_relations(self):
        kg = KnowledgeGraph3D(
            nodes=[
                KGNode(id="A", name="A", type=EntityType.CONCEPT),
                KGNode(id="B", name="B", type=EntityType.CONCEPT),
            ],
            edges=[
                KGEdge(source_node_id="A", target_node_id="B", relationship_name="对比"),
                KGEdge(source_node_id="A", target_node_id="B", relationship_name="依赖"),
            ],
        )
        out = filter_chunk_graph(kg)
        assert len(out.edges) == 1
        assert out.edges[0].relationship_name == "依赖"


class TestPruneGlobalGraph:
    def test_drops_isolated_nodes(self):
        G = nx.DiGraph()
        G.add_node("第1章", type="Chapter")
        G.add_node("栈", type="DataStructure", description="后进先出")
        G.add_edge("第1章", "栈", relationship_name="包含")
        G.add_node("printf", type="Concept", description="")  # 孤立噪声
        prune_global_graph(G)
        assert "printf" not in G
        assert G.number_of_nodes() == 2

    def test_keeps_isolated_nodes_when_no_chapters(self):
        """无章节节点时不剔除孤立节点（无挂载预期，避免清空无标题文档的图）"""
        G = nx.DiGraph()
        G.add_node("TCP", type="Protocol", description="传输控制协议")
        G.add_node("IP", type="Protocol", description="互联网协议")
        prune_global_graph(G)
        assert G.number_of_nodes() == 2

    def test_keeps_chapters_over_scale_cap(self):
        """章节不计入上限：章节全保留，知识点最多保留 max_nodes 个"""
        G = nx.DiGraph()
        G.add_node("第1章", type="Chapter")
        G.add_node("第1.1节", type="Chapter")
        G.add_edge("第1章", "第1.1节", relationship_name="包含")
        for i in range(10):
            G.add_node(f"kp{i}", type="Concept", description="x")
            G.add_edge("第1.1节", f"kp{i}", relationship_name="包含")
        prune_global_graph(G, max_nodes=5)
        assert "第1章" in G  # 章节被保护
        assert "第1.1节" in G
        kp_kept = [n for n in G.nodes if n.startswith("kp")]
        assert len(kp_kept) == 5  # 知识点独占 5 个预算
        assert G.number_of_nodes() == 7  # 2 章节 + 5 知识点

    def test_chapters_exceeding_cap_do_not_eat_kp_budget(self):
        """回归测试：章节数超过上限时，知识点预算不被清零"""
        G = nx.DiGraph()
        for i in range(6):  # 章节数 > max_nodes=5
            G.add_node(f"第{i}章", type="Chapter")
        for i in range(5):
            G.add_edge(f"第{i}章", f"第{i+1}章", relationship_name="包含")
        for i in range(3):
            G.add_node(f"kp{i}", type="Concept", description="x")
            G.add_edge("第5章", f"kp{i}", relationship_name="包含")
        prune_global_graph(G, max_nodes=5)
        # 章节全保留
        assert {f"第{i}章" for i in range(6)} <= set(G.nodes)
        # 知识点未被清零（旧逻辑 max(0, 5-6)=0 会全删）
        assert {f"kp{i}" for i in range(3)} <= set(G.nodes)

    def test_drops_non_vocabulary_edges(self):
        G = nx.DiGraph()
        G.add_node("A", type="Concept", description="x")
        G.add_node("B", type="Concept", description="y")
        G.add_edge("A", "B", relationship_name="对比")
        G.add_edge("A", "B", relationship_name="依赖")
        prune_global_graph(G)
        edges = list(G.edges())
        assert len(edges) == 1
        assert G.edges[edges[0]]["relationship_name"] == "依赖"

    def test_default_max_nodes(self):
        assert MAX_GLOBAL_NODES == 500


class TestExtractorFiltering:
    """KGExtractor 解析后应应用逐 chunk 剪枝"""

    @pytest.mark.asyncio
    async def test_extract_from_chunk_applies_filter(self):
        from app.engines.llm.client import ChatResponse
        from app.kg_pipeline.extraction import KGExtractor
        from app.kg_pipeline.models import DocumentChunk

        class FakeLLM:
            async def chat(self, messages, temperature=0.1, profile=None):
                return ChatResponse(content=(
                    '{"nodes":['
                    '{"id":"printf","name":"printf","type":"Function","description":"输出函数"},'
                    '{"id":"栈","name":"栈","type":"DataStructure","description":"后进先出"}'
                    '],"edges":['
                    '{"source_node_id":"栈","target_node_id":"printf",'
                    '"relationship_name":"对比","description":"x"}'
                    ']}'
                ))

        extractor = KGExtractor(llm_client=FakeLLM())
        chunk = DocumentChunk(text="栈是一种后进先出的数据结构，printf 用于输出。")
        kg = await extractor.extract_from_chunk(chunk)
        assert {n.id for n in kg.nodes} == {"栈"}
        assert kg.edges == []  # 边引用被剪掉的 printf，已删除

    @pytest.mark.asyncio
    async def test_chinese_type_name_kept(self):
        """LLM 返回中文类型名时应映射到规范枚举，核心类型不被剪掉"""
        from app.engines.llm.client import ChatResponse
        from app.kg_pipeline.extraction import KGExtractor
        from app.kg_pipeline.models import DocumentChunk

        class FakeLLM:
            async def chat(self, messages, temperature=0.1, profile=None):
                return ChatResponse(content=(
                    '{"nodes":['
                    '{"id":"快速排序","name":"快速排序","type":"算法","description":"分治排序"},'
                    '{"id":"printf","name":"printf","type":"函数","description":"输出"}'
                    '],"edges":[]}'
                ))

        extractor = KGExtractor(llm_client=FakeLLM())
        chunk = DocumentChunk(text="快速排序是一种分治排序算法，printf 用于输出。")
        kg = await extractor.extract_from_chunk(chunk)
        assert {n.id for n in kg.nodes} == {"快速排序"}
        node = kg.nodes[0]
        assert node.type == EntityType.ALGORITHM  # 中文"算法"→ Algorithm，未被剪掉
