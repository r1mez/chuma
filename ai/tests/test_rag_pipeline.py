"""Tests for RAG pipeline components"""

import httpx
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.engines.rag.embedding import EmbeddingClient
from app.engines.rag.reranker import RerankerClient


class TestEmbeddingClient:
    """EmbeddingClient tests -- all mock vLLM, no real HTTP calls"""

    @pytest.mark.asyncio
    async def test_encode_returns_list_of_floats(self):
        """encode() should return a 1024-dim float list"""
        mock_response = {
            "data": [{"embedding": [0.1] * 1024, "index": 0}]
        }
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            mock_post.return_value = resp_mock

            client = EmbeddingClient(base_url="http://test:8010")
            result = await client.encode("test query")

            assert len(result) == 1024
            assert all(isinstance(v, float) for v in result[:3])

    @pytest.mark.asyncio
    async def test_batch_encode_returns_matching_count(self):
        """batch_encode should return the same number of vectors as input texts"""
        texts = ["text1", "text2", "text3"]
        mock_response = {
            "data": [
                {"embedding": [0.1] * 1024, "index": 0},
                {"embedding": [0.2] * 1024, "index": 1},
                {"embedding": [0.3] * 1024, "index": 2},
            ]
        }
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            mock_post.return_value = resp_mock

            client = EmbeddingClient(base_url="http://test:8010")
            results = await client.batch_encode(texts)

            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_encode_with_retry_retries_on_failure(self):
        """encode_with_retry should retry on httpx errors"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = {"data": [{"embedding": [0.1] * 1024, "index": 0}]}
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            err = httpx.HTTPStatusError("fail", request=None, response=None)
            resp_mock.raise_for_status.side_effect = [
                err, err, None,
            ]
            mock_post.return_value = resp_mock

            client = EmbeddingClient(base_url="http://test:8010")
            result = await client.encode_with_retry("test", retries=2)

            assert len(result) == 1024
            assert resp_mock.raise_for_status.call_count == 3

    @pytest.mark.asyncio
    async def test_encode_with_retry_exhausts_retries(self):
        """should raise after exhausting retries"""
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            err = httpx.HTTPStatusError("fail", request=None, response=None)
            resp_mock.raise_for_status.side_effect = err
            mock_post.return_value = resp_mock

            client = EmbeddingClient(base_url="http://test:8010")
            with pytest.raises(httpx.HTTPStatusError):
                await client.encode_with_retry("test", retries=1)

    @pytest.mark.asyncio
    async def test_query_prefix_is_appended(self):
        """query_prefix should be prepended to the input"""
        mock_response = {
            "data": [{"embedding": [0.1] * 1024, "index": 0}]
        }
        captured_kwargs = {}

        def capture_kwargs(url, **kwargs):
            captured_kwargs.update(kwargs)
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            return resp_mock

        with patch("httpx.AsyncClient.post", side_effect=capture_kwargs):
            client = EmbeddingClient(
                base_url="http://test:8010",
                query_prefix="Represent this sentence for searching: ",
            )
            await client.encode("test query")
            sent_json = captured_kwargs.get("json", {})
            assert sent_json["input"] == "Represent this sentence for searching: test query"


class TestRerankerClient:
    """RerankerClient tests — mock HTTP, no real calls"""

    @pytest.mark.asyncio
    async def test_rerank_returns_scores(self):
        """rerank should return a score list matching the input pair count"""
        pairs = [("q1", "c1"), ("q2", "c2")]
        mock_response = {"scores": [0.95, 0.12]}

        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            mock_post.return_value = resp_mock

            client = RerankerClient(base_url="http://test:8011")
            scores = await client.rerank(pairs)

            assert len(scores) == 2
            assert scores[0] > scores[1]

    @pytest.mark.asyncio
    async def test_rerank_empty_pairs_returns_empty(self):
        """empty input should return an empty list"""
        client = RerankerClient(base_url="http://test:8011")
        scores = await client.rerank([])
        assert scores == []

    @pytest.mark.asyncio
    async def test_rerank_with_top_k_filters(self):
        """top_k should keep only top-K scores and set the rest to -inf"""
        pairs = [("q1", "c1"), ("q2", "c2"), ("q3", "c3")]
        mock_response = {"scores": [0.95, 0.12, 0.50]}

        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            mock_post.return_value = resp_mock

            client = RerankerClient(base_url="http://test:8011")
            scores = await client.rerank(pairs, top_k=2)

            kept = [s for s in scores if s != -float("inf")]
            assert len(kept) == 2
            assert max(scores) == 0.95

    @pytest.mark.asyncio
    async def test_handles_data_format_as_fallback(self):
        """fallback support for {data: [{score: ...}]} response format"""
        pairs = [("q1", "c1")]
        mock_response = {"data": [{"score": 0.88}]}

        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.json.return_value = mock_response
            mock_post.return_value = resp_mock

            client = RerankerClient(base_url="http://test:8011")
            scores = await client.rerank(pairs)
            assert scores == [0.88]

    @pytest.mark.asyncio
    async def test_custom_endpoint(self):
        """support custom endpoint"""
        pairs = [("q1", "c1")]
        mock_response = {"scores": [0.99]}
        captured_url = None

        with patch("httpx.AsyncClient.post") as mock_post:
            def capture(url, **kwargs):
                nonlocal captured_url
                captured_url = url
                resp_mock = MagicMock()
                resp_mock.json.return_value = mock_response
                return resp_mock
            mock_post.side_effect = capture

            client = RerankerClient(
                base_url="http://test:8011",
                endpoint="/score",
            )
            await client.rerank(pairs)
            assert "/score" in captured_url

    @pytest.mark.asyncio
    async def test_rerank_http_error_raised(self):
        """HTTP 4xx/5xx 应抛出 HTTPStatusError"""
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden", request=MagicMock(), response=MagicMock()
            )
            mock_post.return_value = resp_mock

            client = RerankerClient(base_url="http://test:8011")
            with pytest.raises(httpx.HTTPStatusError):
                await client.rerank([("q", "c")])

    @pytest.mark.asyncio
    async def test_rerank_unexpected_format_raises_error(self):
        """未知返回格式应抛出 ValueError"""
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.raise_for_status.return_value = None
            resp_mock.json.return_value = {"unknown": "format"}
            mock_post.return_value = resp_mock

            client = RerankerClient(base_url="http://test:8011")
            with pytest.raises(ValueError, match="(?i)unexpected"):
                await client.rerank([("q", "c")])

    @pytest.mark.asyncio
    async def test_rerank_with_retry_retries_on_failure(self):
        """rerank_with_retry should retry on httpx errors"""
        from unittest.mock import MagicMock
        import httpx
        with patch("httpx.AsyncClient.post") as mock_post:
            resp_mock = MagicMock()
            resp_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
                "fail", request=MagicMock(), response=MagicMock()
            )
            mock_post.return_value = resp_mock
            client = RerankerClient(base_url="http://test:8011")
            with pytest.raises(httpx.HTTPStatusError):
                await client.rerank_with_retry([("q", "c")], retries=1)


class TestDetailLevel:
    def test_enum_values(self):
        from app.engines.rag.pipeline import DetailLevel
        assert DetailLevel.TEXT.value == "text"
        assert DetailLevel.ENTITIES.value == "entities"
        assert DetailLevel.SUBGRAPH.value == "subgraph"


class TestChunkResult:
    def test_default_values(self):
        from app.engines.rag.pipeline import ChunkResult
        r = ChunkResult(chunk_id=1, text="hello", metadata={})
        assert r.cosine_score == 0.0
        assert r.graph_distance == -1
        assert r.entities == []
        assert r.rerank_score == 0.0

    def test_fused_score_default(self):
        from app.engines.rag.pipeline import ChunkResult
        r = ChunkResult(chunk_id=1, text="hello", metadata={})
        assert r.fused_score == 0.0


class TestRagPipeline:
    """RagPipeline integration tests — mock all external dependencies"""

    @pytest.mark.asyncio
    async def test_run_empty_result(self):
        """文档库为空时返回友好提示"""
        from app.engines.rag.pipeline import RagPipeline

        mock_embedder = AsyncMock()
        mock_embedder.encode.return_value = [0.1] * 1024

        with patch(
            "app.engines.rag.pipeline.settings"
        ) as mock_settings:
            mock_settings.PGVECTOR_DSN = ""
            mock_settings.AGE_HOST = "localhost"
            mock_settings.AGE_PORT = 5432
            mock_settings.AGE_DB = "chuma"
            mock_settings.AGE_USER = "postgres"
            mock_settings.AGE_PASSWORD = ""

            pipeline = RagPipeline(embedder=mock_embedder, pg_dsn="postgresql://test/test")

            # Mock _vector_search to return empty
            pipeline._vector_search = AsyncMock(return_value=[])

            result = await pipeline.run("test query", top_k=5)
            assert "未在已上传文档中找到" in result

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocks(self):
        """全链路模拟：embed → search → graph fusion → reranker → format"""
        from app.engines.rag.pipeline import ChunkResult, DetailLevel, RagPipeline

        mock_embedder = AsyncMock()
        mock_embedder.encode.return_value = [0.1] * 1024

        mock_reranker = AsyncMock()
        mock_reranker.rerank.return_value = [0.95, 0.90]

        candidate_chunks = [
            ChunkResult(
                chunk_id=1, text="共享栈的定义", metadata={"entities": ["共享栈"]},
                entities=["共享栈"], chapter_path="第3章 > 3.1",
            ),
            ChunkResult(
                chunk_id=2, text="顺序栈的定义", metadata={"entities": ["顺序栈"]},
                entities=["顺序栈"], chapter_path="第3章 > 3.1",
            ),
        ]
        candidate_chunks[0].cosine_score = 0.9
        candidate_chunks[1].cosine_score = 0.7

        pipeline = RagPipeline(
            embedder=mock_embedder,
            reranker=mock_reranker,
            pg_dsn="postgresql://test/test",
        )

        # Mock internal stages
        pipeline._vector_search = AsyncMock(return_value=candidate_chunks)
        pipeline._graph_fusion = AsyncMock(
            return_value=candidate_chunks  # skip real fusion
        )

        result = await pipeline.run("共享栈", top_k=2, detail_level=DetailLevel.SUBGRAPH)

        assert "共享栈" in result
        assert "第3章" in result
        assert mock_embedder.encode.called
        assert mock_reranker.rerank.called

    def test_detail_level_text(self):
        """TEXT 模式不包含实体和章节信息"""
        from app.engines.rag.pipeline import ChunkResult, DetailLevel, RagPipeline

        r = ChunkResult(
            chunk_id=1, text="共享栈的定义", metadata={},
            entities=["共享栈"], chapter_path="第3章 > 3.1",
        )
        pipeline = RagPipeline(pg_dsn="postgresql://test/test")
        result = pipeline._format_output(
            "共享栈", [r], DetailLevel.TEXT,
        )
        assert "共享栈的定义" in result
        assert "涉及知识点" not in result
        assert "章节路径" not in result

    def test_detail_level_entities(self):
        """ENTITIES 模式包含实体但不包含章节路径"""
        from app.engines.rag.pipeline import ChunkResult, DetailLevel, RagPipeline

        r = ChunkResult(
            chunk_id=1, text="共享栈的定义", metadata={},
            entities=["共享栈"], chapter_path="第3章 > 3.1",
        )
        pipeline = RagPipeline(pg_dsn="postgresql://test/test")
        result = pipeline._format_output(
            "共享栈", [r], DetailLevel.ENTITIES,
        )
        assert "共享栈的定义" in result
        assert "涉及知识点" in result
        assert "章节路径" not in result

    def test_detail_level_subgraph(self):
        """SUBGRAPH 模式包含实体和章节路径"""
        from app.engines.rag.pipeline import ChunkResult, DetailLevel, RagPipeline

        r = ChunkResult(
            chunk_id=1, text="共享栈的定义", metadata={},
            entities=["共享栈"], chapter_path="第3章 > 3.1",
        )
        pipeline = RagPipeline(pg_dsn="postgresql://test/test")
        result = pipeline._format_output(
            "共享栈", [r], DetailLevel.SUBGRAPH,
        )
        assert "共享栈的定义" in result
        assert "涉及知识点" in result
        assert "章节路径" in result

    @pytest.mark.asyncio
    async def test_vector_search_error_returns_empty(self):
        """_vector_search 异常时应返回空列表"""
        from app.engines.rag.pipeline import RagPipeline

        mock_embedder = AsyncMock()
        mock_embedder.encode.return_value = [0.1] * 1024
        pipeline = RagPipeline(embedder=mock_embedder, pg_dsn="postgresql://test/test")
        # Mock asyncpg.connect to throw
        with patch("asyncpg.connect", side_effect=Exception("DB down")):
            result = await pipeline.run("test")
            assert "未在已上传文档中找到" in result

    @pytest.mark.asyncio
    async def test_reranker_fallback_on_failure(self):
        """reranker 异常时降级为融合分排序"""
        from app.engines.rag.pipeline import ChunkResult, RagPipeline

        mock_embedder = AsyncMock()
        mock_embedder.encode.return_value = [0.1] * 1024
        mock_reranker = AsyncMock()
        mock_reranker.rerank.side_effect = Exception("Reranker down")

        pipeline = RagPipeline(
            embedder=mock_embedder,
            reranker=mock_reranker,
            pg_dsn="postgresql://test/test",
        )
        c1 = ChunkResult(chunk_id=1, text="a", metadata={}, fused_score=0.9)
        c2 = ChunkResult(chunk_id=2, text="b", metadata={}, fused_score=0.5)
        pipeline._vector_search = AsyncMock(return_value=[c1, c2])
        pipeline._graph_fusion = AsyncMock(return_value=[c1, c2])

        result = await pipeline.run("test", top_k=2)
        assert isinstance(result, str)
        assert mock_reranker.rerank.called  # it tried

