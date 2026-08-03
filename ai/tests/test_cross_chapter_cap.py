"""跨章节依赖按对上限测试"""

import json

import networkx as nx
import pytest

from app.engines.llm.client import ChatResponse
from app.kg_pipeline.cross_chapter import CrossChapterExtractor, MAX_DEPS_PER_PAIR


class TestCrossChapterCap:
    @pytest.mark.asyncio
    async def test_caps_deps_per_pair(self):
        G = nx.DiGraph()
        G.add_node("第1章", type="Chapter")
        G.add_node("第2章", type="Chapter")
        G.add_node("A1", type="Concept", name="A1")
        G.add_node("B1", type="Concept", name="B1")
        G.add_edge("第1章", "A1", relationship_name="包含")
        G.add_edge("第2章", "B1", relationship_name="包含")

        deps = [
            {"source": "A1", "target": "B1", "relationship": "依赖",
             "description": f"依赖{i}"}
            for i in range(8)
        ]

        class FakeLLM:
            async def chat(self, messages, temperature=0.1, profile=None):
                return ChatResponse(
                    content=json.dumps({"dependencies": deps}, ensure_ascii=False)
                )

        extractor = CrossChapterExtractor(enable=True, llm_client=FakeLLM())
        edges = await extractor.extract(G)
        assert len(edges) == MAX_DEPS_PER_PAIR  # 5

    def test_constant_is_five(self):
        assert MAX_DEPS_PER_PAIR == 5

    @pytest.mark.asyncio
    async def test_malformed_dependencies_does_not_crash(self):
        """dependencies 字段为畸形值（dict 而非 list）时不中止构建"""
        G = nx.DiGraph()
        G.add_node("第1章", type="Chapter")
        G.add_node("第2章", type="Chapter")
        G.add_node("A1", type="Concept", name="A1")
        G.add_node("B1", type="Concept", name="B1")
        G.add_edge("第1章", "A1", relationship_name="包含")
        G.add_edge("第2章", "B1", relationship_name="包含")

        class FakeLLM:
            async def chat(self, messages, temperature=0.1, profile=None):
                return ChatResponse(content=json.dumps({"dependencies": {"bad": "shape"}}))

        extractor = CrossChapterExtractor(enable=True, llm_client=FakeLLM())
        edges = await extractor.extract(G)
        assert edges == []
