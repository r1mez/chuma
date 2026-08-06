"""知识图谱抽取提示词内容测试"""

from app.kg_pipeline.extraction import _load_prompt


class TestKGExtractionPrompt:
    def _prompt(self) -> str:
        return _load_prompt()

    def test_forbids_chapter_titles(self):
        prompt = self._prompt()
        assert "禁止提取章节标题" in prompt

    def test_core_types_listed(self):
        prompt = self._prompt()
        for t in ("Concept", "Algorithm", "DataStructure",
                  "Protocol", "Principle", "Technology"):
            assert t in prompt

    def test_removed_types_explicitly_excluded(self):
        """明确列出不要提取的低价值类型"""
        prompt = self._prompt()
        assert "Function" in prompt
        assert "Operation" in prompt
        assert "Tool" in prompt

    def test_budget_rule(self):
        """逐 chunk 产出预算"""
        prompt = self._prompt()
        assert "3~5" in prompt or "3 到 5" in prompt
        assert "宁缺毋滥" in prompt

    def test_short_description_rule(self):
        """节点描述 20 字以内"""
        prompt = self._prompt()
        assert "20" in prompt

    def test_relation_vocabulary(self):
        """关系名必须来自词表"""
        prompt = self._prompt()
        for rel in ("包含", "属于", "使用", "依赖", "实现",
                    "基于", "组成部分", "前提", "应用"):
            assert rel in prompt
