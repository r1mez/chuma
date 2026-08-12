"""Course-isolated temporal student-knowledge bipartite graph for DyGKT.

DyGKT itself is a temporal bipartite link-classification model.  In this
project the two node partitions are deliberately ``student-in-course`` and
``knowledge-point-in-course`` rather than students and individual questions.
An exercise record therefore creates a labelled interaction between a student
and the knowledge point assessed by that question.  ``course_id`` is part of
both node identities, so components from different subjects cannot become
neighbours or share a knowledge-node feature identity.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.engines.gnn.features import CandidateQuestion, InteractionEvent, normalise_timestamp


KnowledgeKey = tuple[int, str]
StudentCourseKey = tuple[int, int]


@dataclass(frozen=True)
class DyGKTTarget:
    """One labelled or unlabelled student-knowledge link at a graph time."""

    student_node_id: int
    knowledge_node_id: int
    edge_id: int
    timestamp: float
    label: float | None
    event: InteractionEvent | None = None
    candidate: CandidateQuestion | None = None


class TemporalBipartiteGraph:
    """A course-isolated adapter for DyGKT's causal first-hop sampler."""

    RAW_FEATURE_DIM = 64

    def __init__(
        self,
        events: Iterable[InteractionEvent],
        candidates: Iterable[CandidateQuestion] = (),
        skill_to_id: dict[str, int] | None = None,
    ):
        self.events = sorted(
            list(events),
            key=lambda item: (normalise_timestamp(item.created_at), item.course_id, item.stu_id, item.question_id),
        )
        self.candidates = list(candidates)
        student_course_keys = sorted({(event.course_id, event.stu_id) for event in self.events})
        knowledge_keys = sorted(
            {(event.course_id, event.kg_node_name) for event in self.events}
            | {(item.course_id, item.kg_node_name) for item in self.candidates}
        )
        self.student_to_node = {
            student_key: index + 1
            for index, student_key in enumerate(student_course_keys)
        }
        self.knowledge_to_node = {
            knowledge_key: len(self.student_to_node) + index + 1
            for index, knowledge_key in enumerate(knowledge_keys)
        }
        self.node_to_student = {node: student_key for student_key, node in self.student_to_node.items()}
        self.node_to_knowledge = {node: knowledge_key for knowledge_key, node in self.knowledge_to_node.items()}

        self._knowledge_difficulty = self._collect_knowledge_difficulty()
        self._skill_to_id = dict(skill_to_id) if skill_to_id is not None else self._build_skill_ids()
        self._start_time = self._find_start_time()
        self.node_raw_features = self._build_node_features()
        # Original DyGKT pads both raw feature matrices to 64 dimensions and
        # uses edge column 0 as the answer-performance input.
        self.edge_raw_features: list[list[float]] = [[0.0] * self.RAW_FEATURE_DIM]
        self.targets: list[DyGKTTarget] = []
        self._adjacency: list[list[tuple[int, int, float]]] = [
            [] for _ in range(len(self.knowledge_to_node) + len(self.student_to_node) + 1)
        ]
        self._build_edges()
        self._neighbor_times: list[list[float]] = [
            [value[2] for value in adjacency] for adjacency in self._adjacency
        ]

    @staticmethod
    def knowledge_feature_key(course_id: int, knowledge_point: str) -> str:
        """Stable feature key that also keeps same-named cross-course points apart."""

        return f"{int(course_id)}::{knowledge_point}"

    def ensure_student(self, student_id: int, course_id: int) -> int:
        """Add a cold-start student-in-course node without interaction edges."""

        student_key = (course_id, student_id)
        existing = self.student_to_node.get(student_key)
        if existing is not None:
            return existing
        node_id = len(self._adjacency)
        self.student_to_node[student_key] = node_id
        self.node_to_student[node_id] = student_key
        self.node_raw_features.append([0.0] * self.RAW_FEATURE_DIM)
        self._adjacency.append([])
        self._neighbor_times.append([])
        return node_id

    @property
    def skill_to_id(self) -> dict[str, int]:
        """Persisted course-scoped knowledge vocabulary for online consistency."""

        return dict(self._skill_to_id)

    def set_skill_to_id(self, skill_to_id: dict[str, int]) -> None:
        """Reuse the training vocabulary for online feature consistency."""

        self._skill_to_id = dict(skill_to_id)
        self.node_raw_features = self._build_node_features()

    def event_targets(self) -> list[DyGKTTarget]:
        return self.targets

    def candidate_targets(self, stu_id: int, now: datetime) -> list[DyGKTTarget]:
        """Create one prediction target per distinct knowledge point.

        Several questions can assess the same point. DyGKT predicts that
        student--knowledge link once; the planning layer later selects the
        concrete question with that point's predicted probability.
        """

        timestamp = self.to_relative_timestamp(now)
        representatives: dict[KnowledgeKey, CandidateQuestion] = {}
        for item in self.candidates:
            representatives.setdefault((item.course_id, item.kg_node_name), item)
        return [
            DyGKTTarget(
                student_node_id=self.ensure_student(stu_id, course_id),
                knowledge_node_id=self.knowledge_to_node[(course_id, knowledge_point)],
                edge_id=0,
                timestamp=timestamp,
                label=None,
                candidate=candidate,
            )
            for (course_id, knowledge_point), candidate in representatives.items()
        ]

    def get_historical_neighbors(
        self,
        node_ids: list[int],
        timestamps: list[float],
        num_neighbors: int,
    ) -> tuple[list[list[int]], list[list[int]], list[list[float]]]:
        """Match DyGLib's recent first-hop sampler with left zero padding."""

        neighbor_ids: list[list[int]] = []
        edge_ids: list[list[int]] = []
        neighbor_times: list[list[float]] = []
        for node_id, target_time in zip(node_ids, timestamps):
            adjacency = self._adjacency[node_id]
            cutoff = bisect_left(self._neighbor_times[node_id], target_time)
            history = adjacency[max(0, cutoff - num_neighbors):cutoff]
            padding = num_neighbors - len(history)
            neighbor_ids.append([0] * padding + [item[0] for item in history])
            edge_ids.append([0] * padding + [item[1] for item in history])
            neighbor_times.append([0.0] * padding + [item[2] for item in history])
        return neighbor_ids, edge_ids, neighbor_times

    def to_relative_timestamp(self, value: datetime) -> float:
        return max(0.0, (normalise_timestamp(value) - self._start_time).total_seconds())

    def _find_start_time(self):
        if self.events:
            return normalise_timestamp(self.events[0].created_at)
        from datetime import timezone
        return datetime.now(timezone.utc)

    def _collect_knowledge_difficulty(self) -> dict[KnowledgeKey, float]:
        values: dict[KnowledgeKey, list[int]] = {}
        for event in self.events:
            values.setdefault((event.course_id, event.kg_node_name), []).append(event.difficulty)
        for item in self.candidates:
            values.setdefault((item.course_id, item.kg_node_name), []).append(item.difficulty)
        return {
            key: sum(difficulties) / len(difficulties)
            for key, difficulties in values.items()
            if difficulties
        }

    def _build_skill_ids(self) -> dict[str, int]:
        keys = sorted(self.knowledge_to_node)
        return {
            self.knowledge_feature_key(course_id, knowledge_point): index + 1
            for index, (course_id, knowledge_point) in enumerate(keys)
        }

    def _build_node_features(self) -> list[list[float]]:
        features = [
            [0.0] * self.RAW_FEATURE_DIM
            for _ in range(len(self.knowledge_to_node) + len(self.student_to_node) + 1)
        ]
        for knowledge_key, node_id in self.knowledge_to_node.items():
            course_id, knowledge_point = knowledge_key
            features[node_id][0] = float(
                self._skill_to_id.get(self.knowledge_feature_key(course_id, knowledge_point), 0)
            )
            features[node_id][1] = max(
                1.0,
                min(float(self._knowledge_difficulty.get(knowledge_key, 3.0)), 5.0),
            ) / 5.0
        return features

    def _build_edges(self) -> None:
        for event_index, event in enumerate(self.events, start=1):
            source = self.student_to_node[(event.course_id, event.stu_id)]
            destination = self.knowledge_to_node[(event.course_id, event.kg_node_name)]
            timestamp = self.to_relative_timestamp(event.created_at)
            edge_features = [0.0] * self.RAW_FEATURE_DIM
            edge_features[0] = float(event.correctness)
            self.edge_raw_features.append(edge_features)
            self._adjacency[source].append((destination, event_index, timestamp))
            self._adjacency[destination].append((source, event_index, timestamp))
            self.targets.append(DyGKTTarget(
                student_node_id=source,
                knowledge_node_id=destination,
                edge_id=event_index,
                timestamp=timestamp,
                label=float(event.correctness),
                event=event,
            ))

        for adjacency in self._adjacency:
            adjacency.sort(key=lambda item: (item[2], item[1]))
