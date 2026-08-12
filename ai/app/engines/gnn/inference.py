"""Original DyGKT inference and separate learning-plan decision fusion."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from math import exp
from typing import Any, Callable

from app.config import settings
from app.engines.gnn.features import CandidateQuestion, InteractionEvent
from app.engines.gnn.graph import TemporalBipartiteGraph
from app.engines.gnn.repository import CourseRecommendationSnapshot, TGNNRepository

logger = logging.getLogger(__name__)
MODEL_VERSION = "PengLinzhi/DyGKT-main+student-knowledge-course-isolated-v1"


def _rank_index(items: list[int]) -> dict[int, int]:
    return {item_id: index + 1 for index, item_id in enumerate(items)}


def _mentioned_score(knowledge_point: str, text: str | None) -> float:
    return float((text or "").casefold().count((knowledge_point or "").casefold())) if knowledge_point else 0.0


def _cold_start_probability(candidate: CandidateQuestion, mastery: float) -> float:
    """Product fallback only; it is never passed to, or described as, DyGKT."""

    difficulty = max(1, min(candidate.difficulty, 5))
    logit = 1.15 * (mastery / 5.0 - 0.5) - 1.05 * ((difficulty - 3) / 2.0)
    return 1.0 / (1.0 + exp(-logit))


class TGNNInference:
    """DyGKT prediction followed by a model-external learning-plan decision layer."""

    def __init__(
        self,
        repository: TGNNRepository | None = None,
        model_path: str | None = None,
        probability_predictor: Callable[[CandidateQuestion, list[InteractionEvent]], float] | None = None,
    ):
        self.repository = repository or TGNNRepository()
        self.model_path = model_path or settings.TGNN_MODEL_PATH
        self.probability_predictor = probability_predictor
        self._model = None
        self._model_status: str | None = None
        self._history_size = settings.TGNN_HISTORY_SIZE

    async def recommend_for_course(
        self,
        stu_id: int,
        course_id: int,
        top_k: int | None = None,
        ai_analysis: str | None = None,
        teacher_opinion: str | None = None,
    ) -> dict[str, Any]:
        logger.info(
            "[DyGKT 推荐] 开始: stu_id=%s, course_id=%s, top_k=%s, ai_analysis=%s, teacher_opinion=%s",
            stu_id,
            course_id,
            top_k or settings.TGNN_TOP_K,
            bool(ai_analysis and ai_analysis.strip()),
            bool(teacher_opinion and teacher_opinion.strip()),
        )
        snapshot = await asyncio.to_thread(self.repository.load_snapshot, stu_id, course_id)
        logger.info(
            "[DyGKT 推荐] 数据快照: stu_id=%s, course_id=%s, 当前学科有效交互=%s, 当前学科学生历史=%s, 候选题=%s, 已记录掌握度=%s",
            stu_id,
            course_id,
            len(snapshot.events),
            len(snapshot.student_events),
            len(snapshot.candidates),
            len(snapshot.mastery_by_concept),
        )
        return self.rank_snapshot(snapshot, top_k or settings.TGNN_TOP_K, ai_analysis, teacher_opinion)

    def rank_snapshot(
        self,
        snapshot: CourseRecommendationSnapshot,
        top_k: int = 3,
        ai_analysis: str | None = None,
        teacher_opinion: str | None = None,
    ) -> dict[str, Any]:
        if not snapshot.candidates:
            logger.info(
                "[DyGKT 推荐] 无候选题: stu_id=%s, course_id=%s",
                snapshot.stu_id,
                snapshot.course_id,
            )
            return self._empty_result(snapshot, "no_candidates", "该学科暂无未完成且已关联知识点的题目。")

        graph = TemporalBipartiteGraph(snapshot.events, snapshot.candidates)
        candidate_targets = graph.candidate_targets(snapshot.stu_id, datetime.now(timezone.utc))
        logger.info(
            "[DyGKT 推荐] 构图完成: 类型=学生-知识点二部图（课程隔离）, 节点=%s, 历史邻居上限=%s, 待预测知识点=%s, 题目候选=%s",
            len(graph.node_raw_features),
            self._history_size,
            len(candidate_targets),
            len(snapshot.candidates),
        )
        model_probabilities, used_model = self._predict_dygkt(graph, candidate_targets, snapshot)
        probability_by_knowledge = {
            (target.candidate.course_id, target.candidate.kg_node_name): probability
            for target, probability in zip(candidate_targets, model_probabilities)
            if target.candidate is not None
        }
        scored: list[dict[str, Any]] = []
        for candidate in snapshot.candidates:
            probability = probability_by_knowledge[(candidate.course_id, candidate.kg_node_name)]
            mastery = float(snapshot.mastery_by_concept.get(candidate.kg_node_name, 2.5))
            # The following utility is intentionally part of the decision layer,
            # not a DyGKT input. It defines the desired learning challenge.
            challenge_fit = max(0.0, 1.0 - abs(probability - settings.TGNN_TARGET_CORRECT_PROBABILITY) / settings.TGNN_TARGET_CORRECT_PROBABILITY)
            remediation = 1.0 - max(0.0, min(mastery, 5.0)) / 5.0
            scored.append({
                "candidate": candidate,
                "predicted_correct_probability": round(probability, 4),
                "challenge_fit": round(challenge_fit, 4),
                "mastery": round(mastery, 2),
                "utility": round(0.65 * challenge_fit + 0.35 * remediation, 6),
            })

        # === Learning planning decision layer (outside DyGKT) ===
        dygkt_rank = sorted(scored, key=lambda item: (-item["utility"], item["candidate"].question_id))
        mastery_rank = sorted(scored, key=lambda item: (item["mastery"], item["candidate"].question_id))
        ai_rank = sorted((item for item in scored if _mentioned_score(item["candidate"].kg_node_name, ai_analysis) > 0), key=lambda item: (-_mentioned_score(item["candidate"].kg_node_name, ai_analysis), -item["utility"]))
        teacher_rank = sorted((item for item in scored if _mentioned_score(item["candidate"].kg_node_name, teacher_opinion) > 0), key=lambda item: (-_mentioned_score(item["candidate"].kg_node_name, teacher_opinion), -item["utility"]))
        source_ranks = {
            "dygkt": _rank_index([item["candidate"].question_id for item in dygkt_rank]),
            "mastery": _rank_index([item["candidate"].question_id for item in mastery_rank]),
            "ai_analysis": _rank_index([item["candidate"].question_id for item in ai_rank]),
            "teacher_opinion": _rank_index([item["candidate"].question_id for item in teacher_rank]),
        }
        source_weights = {"dygkt": 1.0, "mastery": 0.9, "ai_analysis": 0.65, "teacher_opinion": 0.8}
        for item in scored:
            question_id = item["candidate"].question_id
            ranks = {source: values[question_id] for source, values in source_ranks.items() if question_id in values}
            item["source_ranks"] = ranks
            item["rrf_score"] = round(sum(source_weights[source] / (settings.TGNN_RRF_K + rank) for source, rank in ranks.items()), 8)

        fused = sorted(scored, key=lambda item: (-item["rrf_score"], -item["utility"], item["candidate"].question_id))
        selected: list[dict[str, Any]] = []
        concepts: set[str] = set()
        for item in fused:
            if item["candidate"].kg_node_name in concepts:
                continue
            concepts.add(item["candidate"].kg_node_name)
            selected.append(self._serialise_recommendation(item, len(selected) + 1))
            if len(selected) >= max(1, top_k):
                break
        status = "model" if used_model else ("cold_start_fallback" if len(snapshot.student_events) < settings.TGNN_MIN_HISTORY else "heuristic_fallback")
        active_sources = [source for source, ranks in source_ranks.items() if ranks]
        logger.info(
            "[DyGKT 推荐] 融合排序: status=%s, active_sources=%s, 候选预测概率范围=%.1f%%~%.1f%%",
            status,
            ",".join(active_sources),
            min(probability_by_knowledge.values(), default=0.0) * 100,
            max(probability_by_knowledge.values(), default=0.0) * 100,
        )
        logger.info(
            "[DyGKT 推荐] 最终推荐: %s",
            [
                {
                    "rank": item["rank"],
                    "question_id": item["question_id"],
                    "knowledge_point": item["knowledge_point"],
                    "probability": f"{item['predicted_correct_probability']:.1%}",
                    "rrf_score": item["rrf_score"],
                    "sources": item["source_ranks"],
                }
                for item in selected
            ],
        )
        return {
            "status": status,
            "model_version": MODEL_VERSION if used_model else None,
            "history_event_count": len(snapshot.student_events),
            "candidate_count": len(snapshot.candidates),
            "target_correct_probability": settings.TGNN_TARGET_CORRECT_PROBABILITY,
            "fusion": {"method": "weighted_rrf", "rrf_k": settings.TGNN_RRF_K, "source_weights": source_weights, "active_sources": active_sources},
            "recommendations": selected,
        }

    def _predict_dygkt(self, graph: TemporalBipartiteGraph, targets, snapshot: CourseRecommendationSnapshot) -> tuple[list[float], bool]:
        if self.probability_predictor is not None:
            logger.info("[DyGKT 推荐] 使用测试注入预测器，不加载 checkpoint")
            return [max(0.0, min(1.0, float(self.probability_predictor(target.candidate, snapshot.student_events)))) for target in targets], True
        if len(snapshot.student_events) >= settings.TGNN_MIN_HISTORY:
            logger.info(
                "[DyGKT 推荐] 满足模型门槛: 当前学科 student_history=%s >= min_history=%s，准备加载/复用 checkpoint=%s",
                len(snapshot.student_events),
                settings.TGNN_MIN_HISTORY,
                self.model_path,
            )
            try:
                from app.engines.gnn.model import require_torch
                torch, _ = require_torch()
                model = self._load_model(graph)
                if model is not None:
                    model.eval()
                    with torch.no_grad():
                        scores = torch.sigmoid(model(targets, graph)).detach().cpu().tolist()
                    logger.info("[DyGKT 推荐] 模型推理完成: 预测知识点数=%s", len(scores))
                    return [float(score) for score in scores], True
            except Exception as exc:
                logger.warning("[DyGKT 推荐] 模型推理失败，改用启发式兜底: %s", exc)
        else:
            logger.info(
                "[DyGKT 推荐] 当前学科历史不足: student_history=%s < min_history=%s，使用冷启动兜底",
                len(snapshot.student_events),
                settings.TGNN_MIN_HISTORY,
            )
        return [_cold_start_probability(target.candidate, float(snapshot.mastery_by_concept.get(target.candidate.kg_node_name, 2.5))) for target in targets], False

    def _load_model(self, graph: TemporalBipartiteGraph):
        if self._model_status == "failed":
            return None
        try:
            from app.engines.gnn.model import build_tgnn_model, require_torch
            torch, _ = require_torch()
            if self._model is None:
                if not self.model_path or not os.path.exists(self.model_path):
                    logger.warning("[DyGKT 推荐] checkpoint 不存在: %s", self.model_path)
                    self._model_status = "failed"
                    return None
                checkpoint = torch.load(self.model_path, map_location="cpu")
                if checkpoint.get("model_version") != MODEL_VERSION:
                    logger.warning(
                        "[DyGKT 推荐] 忽略不兼容 checkpoint: path=%s, checkpoint_version=%s, expected_version=%s。"
                        "请按学生-知识点、课程隔离图重新训练。",
                        self.model_path,
                        checkpoint.get("model_version"),
                        MODEL_VERSION,
                    )
                    self._model_status = "failed"
                    return None
                config = checkpoint.get("model_config", {})
                config.pop("implementation", None)
                self._history_size = int(checkpoint.get("history_size", settings.TGNN_HISTORY_SIZE))
                skill_to_id = checkpoint.get("skill_to_id")
                if isinstance(skill_to_id, dict):
                    self._skill_to_id = {str(key): int(value) for key, value in skill_to_id.items()}
                    graph.set_skill_to_id(self._skill_to_id)
                self._model = build_tgnn_model(graph.node_raw_features, graph.edge_raw_features, **config)
                self._model.load_state_dict(checkpoint["model_state_dict"])
                logger.info(
                    "[DyGKT 推荐] checkpoint 已加载: path=%s, version=%s, 训练交互=%s, history_size=%s",
                    self.model_path,
                    checkpoint.get("model_version"),
                    checkpoint.get("training_interaction_count"),
                    self._history_size,
                )
            else:
                # The model weights are shared, while each online request has a
                # fresh course graph. Reapply the persisted vocabulary before
                # its graph features are refreshed in ``forward``.
                checkpoint_skill_to_id = getattr(self, "_skill_to_id", None)
                if checkpoint_skill_to_id:
                    graph.set_skill_to_id(checkpoint_skill_to_id)
                logger.info("[DyGKT 推荐] 复用已加载 checkpoint: %s", self.model_path)
            return self._model
        except Exception as exc:
            logger.warning("Unable to load DyGKT checkpoint %s: %s", self.model_path, exc)
            self._model_status = "failed"
            return None

    @staticmethod
    def _serialise_recommendation(item: dict[str, Any], rank: int) -> dict[str, Any]:
        candidate: CandidateQuestion = item["candidate"]
        probability = item["predicted_correct_probability"]
        reason = "处于适度挑战区间：适合作为下一步练习目标。" if 0.45 <= probability <= 0.8 else ("优先补强：当前预测正确率偏低，应先复习知识点再完成该题。" if probability < 0.45 else "适合作为巩固练习：预计可完成，可用于确认掌握情况。")
        return {"rank": rank, "knowledge_point": candidate.kg_node_name, "question_id": candidate.question_id, "question_difficulty": candidate.difficulty, "question_type": candidate.question_type, "predicted_correct_probability": probability, "current_mastery": item["mastery"], "rrf_score": item["rrf_score"], "source_ranks": item["source_ranks"], "reason": reason}

    @staticmethod
    def _empty_result(snapshot: CourseRecommendationSnapshot, status: str, message: str) -> dict[str, Any]:
        return {"status": status, "model_version": None, "history_event_count": len(snapshot.student_events), "candidate_count": len(snapshot.candidates), "target_correct_probability": settings.TGNN_TARGET_CORRECT_PROBABILITY, "fusion": {"method": "weighted_rrf", "rrf_k": settings.TGNN_RRF_K, "source_weights": {}, "active_sources": []}, "recommendations": [], "message": message}
