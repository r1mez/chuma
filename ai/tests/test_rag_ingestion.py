"""Tests for document ingestion — split_sub_chunks + DocIngestion"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engines.rag.ingestion import split_sub_chunks, DocIngestion
from app.kg_pipeline.models import KnowledgeGraph, KGNode, EntityType

# Mock mineru and OCR modules (not available in local dev environment)
import sys
for _mod in ["mineru", "mineru.cli", "mineru.cli.common", "mineru.cli.doc_analyze",
             "mineru.model", "mineru.model.doc_analyze", "mineru.pipeline",
             "app.ocr.service", "app.ocr.schemas"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.kg_pipeline.pipeline import KGPipeline


class TestSplitSubChunks:
    """子切片分割 — 双向一句重叠"""

    def test_basic_split(self):
        """基本段落分割"""
        text = "第一段内容。这里是第一段。\n\n第二段内容。这里是第二段。\n\n第三段内容。这里是第三段。"
        result = split_sub_chunks(text)
        assert len(result) == 3
        assert all(isinstance(r[0], str) for r in result)
        assert all(isinstance(r[1], int) for r in result)

    def test_overlap_first_chunk(self):
        """首段向后取下一段的首句"""
        text = "第一段第一句。第一段第二句。\n\n第二段第一句。第二段第二句。"
        result = split_sub_chunks(text)
        chunk, idx = result[0]
        # 应包含第一段全部 + "第二段第一句。"
        assert "第一段第一句" in chunk
        assert "第一段第二句" in chunk
        assert "第二段第一句" in chunk
        # 不应包含第二段第二句
        assert "第二段第二句" not in chunk

    def test_overlap_last_chunk(self):
        """末段向前取上一段的末句"""
        text = "第一段第一句。第一段第二句。\n\n第二段第一句。第二段第二句。"
        result = split_sub_chunks(text)
        chunk, idx = result[-1]
        # 应包含"第一段第二句。" + 第二段全部
        assert "第一段第二句" in chunk
        assert "第二段第一句" in chunk
        assert "第二段第二句" in chunk
        # 不应包含第一段第一句
        assert "第一段第一句" not in chunk

    def test_overlap_middle_chunk(self):
        """中间段前后各取一句"""
        text = (
            "第一段第一句。第一段第二句。\n\n"
            "第二段第一句。第二段第二句。\n\n"
            "第三段第一句。第三段第二句。"
        )
        result = split_sub_chunks(text)
        # 中间段（索引1）
        chunk, idx = result[1]
        assert "第一段第二句" in chunk  # 前一句
        assert "第二段第一句" in chunk  # 自身
        assert "第二段第二句" in chunk  # 自身
        assert "第三段第一句" in chunk  # 后一句
        # 不应包含非重叠部分
        assert "第一段第一句" not in chunk
        assert "第三段第二句" not in chunk

    def test_single_paragraph(self):
        """单个段落不重叠"""
        text = "只有一段。包含两句。"
        result = split_sub_chunks(text)
        assert len(result) == 1
        assert result[0][1] == 0
        assert result[0][0] == text

    def test_no_sentence_boundary(self):
        """没有句号的段落整段作一句处理"""
        text = "无句号段落\n\n第二段有句号。继续。"
        result = split_sub_chunks(text)
        assert len(result) == 2


class TestDocIngestion:
    """DocIngestion tests — mock all external calls"""

    @pytest.mark.asyncio
    async def test_ingest_empty_chunks(self):
        """空输入返回 0"""
        ingestor = DocIngestion(pg_dsn="postgresql://test/test")
        count = await ingestor.ingest([], {})
        assert count == 0

    @pytest.mark.asyncio
    async def test_ingest_with_mocked_embedder(self):
        """带 mock embedder 的全流程"""
        mock_embedder = AsyncMock()
        mock_embedder.batch_encode.return_value = [[0.1] * 1024, [0.2] * 1024]

        ingestor = DocIngestion(
            embedder=mock_embedder,
            pg_dsn="postgresql://test/test",
        )

        # Mock _batch_insert
        ingestor._batch_insert = AsyncMock(return_value=2)

        from app.kg_pipeline.models import DocumentChunk
        chunks = [
            DocumentChunk(
                text="段落A的内容。包含几句。\n\n段落B的内容。也包含几句。",
                chunk_index=0,
                heading_path=["第3章", "3.1"],
            ),
        ]
        entities_per_chunk = {0: ["实体A", "实体B"]}

        count = await ingestor.ingest(
            chunks=chunks,
            entities_per_chunk=entities_per_chunk,
            course_id=1,
            source="test.md",
        )

        assert count == 2
        assert mock_embedder.batch_encode.called
        assert ingestor._batch_insert.called


class TestKGPipelineStep7:
    """KGPipeline Step 7 (pgvector ingestion) integration"""

    @pytest.mark.asyncio
    async def test_step7_called_after_age_storage(self):
        """Step 7 应在 AGE Storage 之后被调用"""
        mock_storage = MagicMock()
        mock_storage.initialize_graph.return_value = None
        mock_storage.write_graph.return_value = 5

        mock_extractor = AsyncMock()
        mock_extractor.extract_from_chunk.return_value = KnowledgeGraph(
            nodes=[KGNode(id="test", name="test", type=EntityType.CONCEPT)],
            edges=[],
        )

        # Mock DocIngestion
        with patch("app.kg_pipeline.pipeline.DocIngestion") as MockIngestion:
            mock_ingestor = AsyncMock()
            mock_ingestor.ingest.return_value = 3
            MockIngestion.return_value = mock_ingestor

            pipeline = KGPipeline(
                extractor=mock_extractor,
                storage=mock_storage,
                enable_cross_chapter=False,
            )

            md = "## 第1章\n\n内容第一句。内容第二句。\n\n### 1.1\n\n子章节内容。\n"
            result = await pipeline.run_from_markdown(md)

            assert result.status == "completed"
            # Verify DocIngestion.ingest was called
            mock_ingestor.ingest.assert_called_once()
            call_args = mock_ingestor.ingest.call_args
            assert "chunks" in call_args.kwargs
            assert "entities_per_chunk" in call_args.kwargs
