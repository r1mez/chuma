"""Shared, dependency-free feature construction for the TGNN recommender.

The production model follows the DyGKT idea from the research note: a student
history and a question history are treated as two temporal one-hop
neighbourhoods.  This module deliberately contains no database or PyTorch
code, so training, online inference, and unit tests all build identical
features.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Iterable


@dataclass(frozen=True)
class InteractionEvent:
    """One exercise record, projected to a student-knowledge interaction edge."""

    stu_id: int
    question_id: int
    course_id: int
    kg_node_name: str
    difficulty: int
    correctness: int
    created_at: datetime


@dataclass(frozen=True)
class CandidateQuestion:
    """A not-yet-attempted question eligible for the next learning step."""

    question_id: int
    course_id: int
    kg_node_name: str
    difficulty: int
    question_type: str = ""


def normalise_timestamp(value: datetime) -> datetime:
    """Return a timezone-aware UTC timestamp for safe elapsed-time features."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def elapsed_hours(current: datetime, previous: datetime | None) -> float:
    """Elapsed hours, clipped to the range used by the temporal encoder."""

    if previous is None:
        return 0.0
    delta = (normalise_timestamp(current) - normalise_timestamp(previous)).total_seconds()
    return max(0.0, min(delta / 3600.0, 24.0 * 90.0))


def dual_time_features(hours: float, short_gap_hours: float = 24.0) -> tuple[float, float]:
    """Expose DyGKT's short-session and long-gap signals without leakage.

    The neural model learns separate MLPs over this split.  The heuristic
    fallback consumes the same two values, keeping its behaviour explainable
    and aligned with the trained path.
    """

    scaled = min(hours, 24.0 * 90.0)
    if scaled <= short_gap_hours:
        return (scaled / short_gap_hours, 0.0)
    # A saturating long-gap feature represents forgetting rather than making a
    # months-old interaction dominate the entire sequence.
    return (0.0, min(1.0, (scaled - short_gap_hours) / (24.0 * 30.0)))


def build_sequence_features(
    events: Iterable[InteractionEvent],
    mastery_by_concept: dict[str, float] | None = None,
) -> tuple[list[int], list[list[float]], list[float]]:
    """Encode an ordered one-hop event neighbourhood.

    Each event exposes: performance (separate embedding), normalised question
    difficulty, repeat-question indicator, repeat-concept indicator, current
    knowledge mastery, and elapsed time.  Repetition flags correspond to the
    report's multiset indicator and are calculated only from preceding events.
    """

    ordered = sorted(events, key=lambda item: normalise_timestamp(item.created_at))
    mastery_by_concept = mastery_by_concept or {}
    question_counts: Counter[int] = Counter()
    concept_counts: Counter[str] = Counter()
    performances: list[int] = []
    numeric_features: list[list[float]] = []
    gaps: list[float] = []
    previous_time: datetime | None = None

    for event in ordered:
        gap = elapsed_hours(event.created_at, previous_time)
        performances.append(1 if event.correctness else 0)
        numeric_features.append([
            max(1, min(int(event.difficulty or 3), 5)) / 5.0,
            1.0 if question_counts[event.question_id] else 0.0,
            1.0 if concept_counts[event.kg_node_name] else 0.0,
            max(0.0, min(float(mastery_by_concept.get(event.kg_node_name, 2.5)), 5.0)) / 5.0,
        ])
        gaps.append(gap)
        question_counts[event.question_id] += 1
        concept_counts[event.kg_node_name] += 1
        previous_time = event.created_at

    return performances, numeric_features, gaps


def candidate_features(
    candidate: CandidateQuestion,
    student_events: Iterable[InteractionEvent],
    question_events: Iterable[InteractionEvent],
    mastery_by_concept: dict[str, float] | None = None,
    now: datetime | None = None,
) -> list[float]:
    """Create the current edge features used by the final link classifier."""

    student_events = list(student_events)
    question_events = list(question_events)
    mastery_by_concept = mastery_by_concept or {}
    now = now or datetime.now(timezone.utc)

    mastery = max(0.0, min(float(mastery_by_concept.get(candidate.kg_node_name, 2.5)), 5.0))
    question_pass_rate = (
        sum(event.correctness for event in question_events) / len(question_events)
        if question_events else 0.5
    )
    last_student_event = max(
        (event.created_at for event in student_events),
        key=normalise_timestamp,
        default=None,
    )
    inactivity_days = min(elapsed_hours(now, last_student_event) / 24.0, 30.0) / 30.0
    return [
        max(1, min(int(candidate.difficulty or 3), 5)) / 5.0,
        mastery / 5.0,
        max(0.0, min(question_pass_rate, 1.0)),
        inactivity_days,
    ]


def fallback_correct_probability(
    candidate: CandidateQuestion,
    student_events: Iterable[InteractionEvent],
    question_events: Iterable[InteractionEvent],
    mastery_by_concept: dict[str, float] | None = None,
) -> float:
    """A calibrated, explainable fallback used until a trained checkpoint exists.

    It is not labelled as a TGNN-model prediction.  It only allows the product
    to keep producing useful plans while the scheduled/offline training job has
    not yet produced a checkpoint.
    """

    student_events = list(student_events)
    question_events = list(question_events)
    mastery_by_concept = mastery_by_concept or {}
    recent_student_events = sorted(
        student_events, key=lambda item: normalise_timestamp(item.created_at), reverse=True
    )[:10]
    recent_accuracy = (
        sum(event.correctness for event in recent_student_events) / len(recent_student_events)
        if recent_student_events else 0.5
    )
    mastery = float(mastery_by_concept.get(candidate.kg_node_name, 2.5)) / 5.0
    question_pass_rate = (
        sum(event.correctness for event in question_events) / len(question_events)
        if question_events else 0.5
    )
    concept_attempts = sum(
        1 for event in student_events if event.kg_node_name == candidate.kg_node_name
    )
    # Blend current performance, concept mastery, observed item difficulty, and
    # a small repeat-concept effect.  The logistic transform keeps a stable
    # probability interface for RRF ranking and the UI.
    logit = (
        1.35 * (recent_accuracy - 0.5)
        + 1.15 * (mastery - 0.5)
        + 0.9 * (question_pass_rate - 0.5)
        - 1.05 * ((max(1, min(candidate.difficulty, 5)) - 3) / 2.0)
        + min(concept_attempts, 5) * 0.04
    )
    return round(1.0 / (1.0 + exp(-logit)), 4)
