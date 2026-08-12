"""Training pipeline for the original DyGKT computation graph.

Unlike the previous prototype, the model sees no mastery, RRF, teacher or LLM
features. It only receives a course-isolated temporal student-knowledge graph:
node raw features, binary answer edge features, timestamps and causal first-hop
neighbours.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from app.config import settings
from app.engines.gnn.features import InteractionEvent
from app.engines.gnn.graph import DyGKTTarget, TemporalBipartiteGraph
from app.engines.gnn.model import build_tgnn_model, require_torch
from app.engines.gnn.repository import TGNNRepository

logger = logging.getLogger(__name__)
MODEL_VERSION = "PengLinzhi/DyGKT-main+student-knowledge-course-isolated-v1"


def build_training_examples(
    events: Iterable[InteractionEvent],
    history_size: int,
) -> list[DyGKTTarget]:
    """Compatibility helper returning original causal link-classification targets."""

    # ``history_size`` is deliberately unused here: DyGKT samples its most
    # recent L neighbours at each target from the course-isolated component.
    return TemporalBipartiteGraph(events).event_targets()


def _binary_metrics(probabilities: list[float], labels: list[float]) -> dict[str, float]:
    if not labels:
        return {"loss": 0.0, "accuracy": 0.0, "auc": 0.0, "average_precision": 0.0}
    accuracy = sum((value >= 0.5) == (label >= 0.5) for value, label in zip(probabilities, labels)) / len(labels)
    positives = sum(label >= 0.5 for label in labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        auc = 0.0
    else:
        wins = 0.0
        for probability, label in zip(probabilities, labels):
            if label < 0.5:
                continue
            for other_probability, other_label in zip(probabilities, labels):
                if other_label >= 0.5:
                    continue
                wins += 1.0 if probability > other_probability else 0.5 if probability == other_probability else 0.0
        auc = wins / (positives * negatives)
    if not positives:
        average_precision = 0.0
    else:
        ranked = sorted(zip(probabilities, labels), key=lambda item: item[0], reverse=True)
        hits = 0
        precision_sum = 0.0
        for index, (_, label) in enumerate(ranked, start=1):
            if label >= 0.5:
                hits += 1
                precision_sum += hits / index
        average_precision = precision_sum / positives
    return {
        "accuracy": round(accuracy, 6),
        "auc": round(auc, 6),
        "average_precision": round(average_precision, 6),
    }


def _predict_batches(model, graph: TemporalBipartiteGraph, targets: list[DyGKTTarget], batch_size: int):
    torch, _ = require_torch()
    probabilities: list[float] = []
    labels: list[float] = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(targets), batch_size):
            batch = targets[start:start + batch_size]
            probabilities.extend(torch.sigmoid(model(batch, graph)).detach().cpu().tolist())
            labels.extend(float(target.label) for target in batch if target.label is not None)
    return probabilities, labels


def train_model(
    events: Iterable[InteractionEvent],
    output_path: str | Path | None = None,
    history_size: int | None = None,
    epochs: int | None = None,
    batch_size: int | None = None,
    learning_rate: float | None = None,
    min_samples: int | None = None,
) -> dict[str, object]:
    """Train original DyGKT with chronological link-classification batches."""

    torch, nn = require_torch()
    num_neighbors = history_size or settings.TGNN_HISTORY_SIZE
    epochs = epochs or settings.TGNN_TRAIN_EPOCHS
    batch_size = batch_size or settings.TGNN_TRAIN_BATCH_SIZE
    learning_rate = learning_rate or settings.TGNN_TRAIN_LEARNING_RATE
    min_samples = min_samples or settings.TGNN_TRAIN_MIN_SAMPLES
    graph = TemporalBipartiteGraph(events)
    targets = graph.event_targets()
    if len(targets) < min_samples:
        raise ValueError(f"DyGKT 训练交互不足：当前 {len(targets)}，至少需要 {min_samples}。")

    validation_count = max(1, int(len(targets) * 0.2))
    train_targets = targets[:-validation_count]
    validation_targets = targets[-validation_count:]
    if not train_targets:
        raise ValueError("DyGKT 训练集为空，请增加历史交互数据。")

    torch.manual_seed(42)
    model = build_tgnn_model(
        node_raw_features=graph.node_raw_features,
        edge_raw_features=graph.edge_raw_features,
        num_neighbors=num_neighbors,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    loss_fn = nn.BCELoss()
    final_loss = 0.0
    for epoch in range(epochs):
        model.train()
        losses: list[float] = []
        # Original DyGKT keeps temporal batches in chronological order.
        for start in range(0, len(train_targets), batch_size):
            batch = train_targets[start:start + batch_size]
            labels = torch.tensor([target.label for target in batch], dtype=torch.float32)
            optimizer.zero_grad()
            probabilities = torch.sigmoid(model(batch, graph))
            loss = loss_fn(probabilities, labels)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))
        final_loss = sum(losses) / max(len(losses), 1)
        if (epoch + 1) == epochs or (epoch + 1) % 5 == 0:
            probabilities, labels = _predict_batches(model, graph, validation_targets, batch_size)
            metrics = _binary_metrics(probabilities, labels)
            logger.info(
                "[DyGKT] epoch=%s/%s train_loss=%.6f val_accuracy=%s val_auc=%s val_ap=%s",
                epoch + 1, epochs, final_loss, metrics["accuracy"], metrics["auc"], metrics["average_precision"],
            )

    probabilities, labels = _predict_batches(model, graph, validation_targets, batch_size)
    metrics = _binary_metrics(probabilities, labels)
    metrics["loss"] = round(final_loss, 6)
    destination = Path(output_path or settings.TGNN_MODEL_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_config": model.model_config,
        "history_size": num_neighbors,
        "metrics": metrics,
        "training_interaction_count": len(targets),
        "model_version": MODEL_VERSION,
        "graph_schema": "student-knowledge/course-isolated/v1",
        "skill_to_id": graph.skill_to_id,
    }
    torch.save(checkpoint, destination)
    return {
        "output_path": str(destination),
        "training_interaction_count": len(targets),
        "train_interaction_count": len(train_targets),
        "validation_interaction_count": len(validation_targets),
        "metrics": metrics,
        "model_version": MODEL_VERSION,
    }


def train_from_repository(
    course_ids: Iterable[int] | None = None,
    repository: TGNNRepository | None = None,
    **kwargs,
) -> dict[str, object]:
    """Train with course-isolated student-knowledge graph components.

    The graph object contains all selected courses for batching efficiency, but
    every node key includes ``course_id``. Thus neither a student nor a
    knowledge point can have an edge or a sampled neighbour in another course.
    """

    repository = repository or TGNNRepository()
    selected_courses = list(course_ids) if course_ids is not None else repository.list_course_ids()
    # Course-scoped node identities keep disconnected course components inside
    # one DyGKT batch graph. Filtering is retained for targeted retraining.
    events = repository.load_events()
    if course_ids is not None:
        selected = {int(course_id) for course_id in selected_courses}
        events = [event for event in events if event.course_id in selected]
    result = train_model(events, **kwargs)
    result["course_ids"] = selected_courses
    result["event_count"] = len(events)
    return result
