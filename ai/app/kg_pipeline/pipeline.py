"""知识图谱构建 Pipeline — 端到端调度"""

import logging
import os
import tempfile
from typing import Optional

from app.config import settings
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
        """调用 OCR 服务解析文档为 Markdown"""
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
            file_names = await ocr_parse_files(
                output_dir=output_dir,
                uploads=[upload],
                params=OcrParseParams(),
                server_url=settings.OCR_VLM_URL,  # IMPORTANT: use actual OCR URL from settings
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
        """逐块进行 LLM 抽取"""
        chunk_graphs: list[KnowledgeGraph] = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            logger.info(f"[KG] Extracting chunk {i + 1}/{total}")
            kg = await self.extractor.extract_from_chunk(chunk)
            chunk_graphs.append(kg)

        return chunk_graphs

    async def run_from_markdown(self, markdown_text: str) -> PipelineResult:
        """从 Markdown 文本直接构建知识图谱（跳过 OCR）"""
        logger.info("[KG] Phase: Chunking")
        chunks = self.chunker.chunk(markdown_text)
        logger.info(f"[KG] Generated {len(chunks)} chunks")

        logger.info("[KG] Phase: LLM Extraction")
        chunk_graphs = await self._extract_all_chunks(chunks)

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
        """从原始文档文件构建知识图谱（PDF → OCR → KG）"""
        logger.info(f"[KG] Starting pipeline for: {file_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                logger.info("[KG] Phase: OCR Parsing")
                md_content = await self._parse_document(file_path, tmpdir)
                logger.info(f"[KG] OCR completed, Markdown length: {len(md_content)} chars")
            except OcrServiceError as e:
                logger.error(f"[KG] OCR failed: {e}")
                return PipelineResult(status="failed", error=str(e))

            try:
                return await self.run_from_markdown(md_content)
            except Exception as e:
                logger.error(f"[KG] Pipeline failed after OCR: {e}", exc_info=True)
                return PipelineResult(status="failed", error=str(e))
