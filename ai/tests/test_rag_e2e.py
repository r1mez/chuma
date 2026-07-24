"""End-to-end RAG pipeline tests -- require real PostgreSQL + pgvector

These tests run against the local dev database.
Skip with: pytest -m "not e2e"
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.engines.rag.pipeline import RagPipeline, DetailLevel


pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_pipeline_connects_and_returns_text():
    """真实数据库连接测试 -- text 模式"""
    pipeline = RagPipeline()
    result = await pipeline.run("测试", top_k=3)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_pipeline_entities_mode():
    """真实数据库连接测试 -- entities 模式"""
    pipeline = RagPipeline()
    result = await pipeline.run("测试", top_k=3, detail_level=DetailLevel.ENTITIES)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_pipeline_subgraph_mode():
    """真实数据库连接测试 -- subgraph 模式"""
    pipeline = RagPipeline()
    result = await pipeline.run("测试", top_k=3, detail_level=DetailLevel.SUBGRAPH)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_pipeline_with_course_filter():
    """按课程过滤"""
    pipeline = RagPipeline()
    result = await pipeline.run("测试", top_k=3, course_id=1)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_ingestion_round_trip():
    """入库 -> 查询 回环测试

    需要明确知道数据库当前状态，此测试只验证流程不抛异常。
    """
    from app.kg_pipeline.models import DocumentChunk
    from app.engines.rag.ingestion import DocIngestion

    chunks = [
        DocumentChunk(
            text="栈是一种先进后出的线性表。栈的基本操作包括初始化、进栈、出栈、取栈顶元素。",
            chunk_index=0,
            heading_path=["第3章 栈和队列", "3.1 栈"],
        ),
    ]
    entities_per_chunk = {0: ["栈", "进栈", "出栈"]}

    ingestor = DocIngestion()
    count = await ingestor.ingest(
        chunks=chunks,
        entities_per_chunk=entities_per_chunk,
        course_id=1,
        source="e2e_test",
    )
    assert count > 0

    # Now query it back
    pipeline = RagPipeline()
    result = await pipeline.run("栈", top_k=5, detail_level=DetailLevel.SUBGRAPH)
    assert "栈" in result
