from __future__ import annotations

from app.kg_pipeline.models import KGNode, KGEdge, KnowledgeGraph, DocumentChunk, EntityType
from app.kg_pipeline.chunking import MarkdownChunker
from app.kg_pipeline.extraction import KGExtractor
from app.kg_pipeline.graph_builder import GraphBuilder
from app.kg_pipeline.storage import AgeStorage

# 延迟导入 pipeline（需要 mineru，仅在远程服务器可用）
def get_pipeline() -> type:
    from app.kg_pipeline.pipeline import KGPipeline, PipelineResult  # noqa: F811
    return KGPipeline

def get_pipeline_result() -> type:
    from app.kg_pipeline.pipeline import PipelineResult
    return PipelineResult

__all__ = [
    "KGNode", "KGEdge", "KnowledgeGraph", "DocumentChunk", "EntityType",
    "MarkdownChunker", "KGExtractor", "GraphBuilder", "AgeStorage",
]
