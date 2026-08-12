"""PostgreSQL data access for TGNN training and online recommendation."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from app.config import settings
from app.engines.gnn.features import CandidateQuestion, InteractionEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CourseRecommendationSnapshot:
    """All causal data necessary to rank one student's next practice targets."""

    stu_id: int
    course_id: int
    events: list[InteractionEvent]
    candidates: list[CandidateQuestion]
    mastery_by_concept: dict[str, float]

    @property
    def student_events(self) -> list[InteractionEvent]:
        """Only this student's interactions in the current subject component."""

        return [
            event for event in self.events
            if event.stu_id == self.stu_id and event.course_id == self.course_id
        ]

    @property
    def events_by_question(self) -> dict[int, list[InteractionEvent]]:
        grouped: dict[int, list[InteractionEvent]] = defaultdict(list)
        for event in self.events:
            grouped[event.question_id].append(event)
        return grouped


class TGNNRepository:
    """Synchronous repository; callers should use it through ``asyncio.to_thread``."""

    def _connect(self):
        connection = psycopg2.connect(
            host=settings.AGE_HOST,
            port=settings.AGE_PORT,
            dbname=settings.AGE_DB,
            user=settings.AGE_USER,
            password=settings.AGE_PASSWORD,
        )
        connection.set_session(autocommit=True)
        return connection

    @staticmethod
    def _event_from_row(row: dict[str, Any]) -> InteractionEvent:
        return InteractionEvent(
            stu_id=int(row["stu_id"]),
            question_id=int(row["question_id"]),
            course_id=int(row["course_id"]),
            kg_node_name=str(row.get("kg_node_name") or "未标注知识点"),
            difficulty=max(1, min(int(row.get("difficulty") or 3), 5)),
            correctness=1 if row.get("correctness") else 0,
            created_at=row["created_at"],
        )

    def load_events(self, course_id: int | None = None) -> list[InteractionEvent]:
        """Load labelled interactions in chronological order.

        Course IDs are retained on every interaction. The graph adapter makes
        both student and knowledge node identities course-scoped, so loading
        all events cannot create cross-subject temporal neighbours.
        """

        connection = self._connect()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        er.stu_id,
                        er.question_id,
                        er.course_id,
                        COALESCE(NULLIF(TRIM(er.kg_node_name), ''),
                                 NULLIF(TRIM(q.kg_node_name), ''), '未标注知识点') AS kg_node_name,
                        COALESCE(er.question_difficulty, q.question_difficulty, 3) AS difficulty,
                        CASE
                            WHEN er.do_istrue IS NOT NULL THEN CASE WHEN er.do_istrue THEN 1 ELSE 0 END
                            WHEN er.do_score IS NOT NULL THEN CASE WHEN er.do_score >= 6 THEN 1 ELSE 0 END
                            ELSE NULL
                        END AS correctness,
                        er.created_at
                    FROM exercise_records er
                    JOIN questions q ON q.question_id = er.question_id
                    WHERE er.created_at IS NOT NULL
                      AND (er.do_istrue IS NOT NULL OR er.do_score IS NOT NULL)
                      AND (%s IS NULL OR er.course_id = %s)
                    ORDER BY er.created_at ASC, er.do_id ASC
                    """,
                    (course_id, course_id),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        return [self._event_from_row(dict(row)) for row in rows]

    def load_candidates(self, stu_id: int, course_id: int) -> list[CandidateQuestion]:
        """Return unattempted, knowledge-point-linked questions for the learner."""

        connection = self._connect()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT q.question_id, q.course_id, q.kg_node_name,
                           q.question_difficulty, q.question_type
                    FROM questions q
                    WHERE q.course_id = %s
                      AND NULLIF(TRIM(q.kg_node_name), '') IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM exercise_records er
                          WHERE er.stu_id = %s AND er.question_id = q.question_id
                      )
                    ORDER BY q.question_id ASC
                    """,
                    (course_id, stu_id),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        return [
            CandidateQuestion(
                question_id=int(row["question_id"]),
                course_id=int(row["course_id"]),
                kg_node_name=str(row["kg_node_name"]),
                difficulty=max(1, min(int(row.get("question_difficulty") or 3), 5)),
                question_type=str(row.get("question_type") or ""),
            )
            for row in rows
        ]

    def load_mastery(self, stu_id: int, course_id: int) -> dict[str, float]:
        connection = self._connect()
        try:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT kg_node_name, kg_degree
                    FROM student_knowledge_mastery
                    WHERE stu_id = %s AND course_id = %s
                    """,
                    (stu_id, course_id),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        return {
            str(row["kg_node_name"]): float(row.get("kg_degree") or 0.0)
            for row in rows
            if row.get("kg_node_name")
        }

    def load_snapshot(self, stu_id: int, course_id: int) -> CourseRecommendationSnapshot:
        return CourseRecommendationSnapshot(
            stu_id=stu_id,
            course_id=course_id,
            # Online inference operates on one course component only. Training
            # can still batch all courses because graph node identities are
            # course-scoped.
            events=self.load_events(course_id),
            candidates=self.load_candidates(stu_id, course_id),
            mastery_by_concept=self.load_mastery(stu_id, course_id),
        )

    def list_course_ids(self) -> list[int]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT course_id FROM courses ORDER BY course_id")
                return [int(row[0]) for row in cursor.fetchall()]
        finally:
            connection.close()
