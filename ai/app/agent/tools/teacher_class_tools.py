"""Read-only tools for the teacher class assistant.

Every tool derives its teacher/class/course scope from AgentContext. Scope values
are never accepted from the model as free-form SQL parameters.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg2
import psycopg2.extras

from app.agent.context import current_agent_context
from app.agent.tool_registry import ToolRegistry
from app.config import settings

logger = logging.getLogger(__name__)


CLASS_TOOL_NAMES = frozenset(
    {
        "teacher_query_class_overview",
        "teacher_query_class_mastery",
        "teacher_query_difficult_knowledge",
        "teacher_query_student_risk",
        "teacher_query_student_profile",
    }
)


def _context_scope() -> tuple[int, int, int]:
    context = current_agent_context.get()
    if context is None or context.user_role != "teacher":
        raise PermissionError("Teacher class tools require a teacher AgentContext")

    teacher_id = context.teacher_id or context.user_id
    if context.class_id is None or context.course_id is None:
        raise ValueError("class_id and course_id are required for class tools")
    return teacher_id, context.class_id, context.course_id


def _get_conn():
    conn = psycopg2.connect(
        host=settings.AGE_HOST,
        port=settings.AGE_PORT,
        dbname=settings.AGE_DB,
        user=settings.AGE_USER,
        password=settings.AGE_PASSWORD,
    )
    conn.set_session(autocommit=True)
    return conn


def _check_scope(cur, teacher_id: int, class_id: int, course_id: int) -> None:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM teacher_class tc
            JOIN teacher_course tcourse ON tcourse.tea_id = tc.tea_id
            WHERE tc.tea_id = %s
              AND tc.class_id = %s
              AND tcourse.course_id = %s
        ) AS allowed
        """,
        (teacher_id, class_id, course_id),
    )
    if not cur.fetchone()["allowed"]:
        raise PermissionError("Teacher has no access to this class and course")


def _result(tool: str, data: Any) -> str:
    return json.dumps(
        {"tool": tool, "success": True, "data": data},
        ensure_ascii=False,
        default=str,
    )


def _error(tool: str, message: str) -> str:
    logger.warning("%s failed: %s", tool, message)
    return json.dumps(
        {"tool": tool, "success": False, "error": message},
        ensure_ascii=False,
    )


def _limit(value: int) -> int:
    return max(1, min(int(value), 20))


@ToolRegistry.register(
    name="teacher_query_class_overview",
    description="查询当前教师所选班级和学科的整体学情概览，包括学生人数、平均进度、平均掌握度和做题情况。",
    parameters={
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
)
async def query_class_overview(user_id: int) -> str:
    tool = "teacher_query_class_overview"
    try:
        teacher_id, class_id, course_id = _context_scope()
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _check_scope(cur, teacher_id, class_id, course_id)
                cur.execute(
                    """
                    SELECT
                        c.class_id,
                        c.class_name,
                        co.course_id,
                        co.course_name,
                        COUNT(DISTINCT s.stu_id) AS student_count,
                        ROUND(AVG(scm.course_process)::numeric, 4) AS avg_process,
                        ROUND(AVG(scm.course_degree)::numeric, 4) AS avg_mastery,
                        COUNT(DISTINCT er.do_id) AS exercise_count,
                        COUNT(DISTINCT er.stu_id) AS active_student_count,
                        ROUND(AVG(
                            CASE
                                WHEN er.do_istrue IS NOT NULL THEN
                                    CASE WHEN er.do_istrue THEN 1.0 ELSE 0.0 END
                                WHEN er.do_score IS NOT NULL THEN er.do_score / 10.0
                            END
                        )::numeric, 4) AS avg_exercise_accuracy
                    FROM classes c
                    JOIN courses co ON co.course_id = %s
                    LEFT JOIN students s ON s.class_id = c.class_id
                    LEFT JOIN student_course_mastery scm
                        ON scm.stu_id = s.stu_id AND scm.course_id = co.course_id
                    LEFT JOIN exercise_records er
                        ON er.stu_id = s.stu_id AND er.course_id = co.course_id
                    WHERE c.class_id = %s
                    GROUP BY c.class_id, c.class_name, co.course_id, co.course_name
                    """,
                    (course_id, class_id),
                )
                row = cur.fetchone()
                return _result(tool, dict(row) if row else {})
        finally:
            conn.close()
    except Exception as exc:
        return _error(tool, str(exc))


@ToolRegistry.register(
    name="teacher_query_class_mastery",
    description="查询当前班级在当前学科下掌握度最低的知识点，并返回平均掌握度和涉及学生数。",
    parameters={
        "type": "object",
        "properties": {
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
)
async def query_class_mastery(user_id: int, top_k: int = 10) -> str:
    tool = "teacher_query_class_mastery"
    try:
        teacher_id, class_id, course_id = _context_scope()
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _check_scope(cur, teacher_id, class_id, course_id)
                cur.execute(
                    """
                    SELECT
                        skm.kg_node_name AS knowledge_name,
                        ROUND(AVG(skm.kg_degree)::numeric, 4) AS avg_mastery,
                        COUNT(DISTINCT skm.stu_id) AS student_count,
                        COALESCE(SUM(skm.answered_count), 0) AS answered_count,
                        COALESCE(SUM(skm.correct_count), 0) AS correct_count
                    FROM student_knowledge_mastery skm
                    JOIN students s ON s.stu_id = skm.stu_id
                    WHERE s.class_id = %s
                      AND skm.course_id = %s
                    GROUP BY skm.kg_node_name
                    ORDER BY avg_mastery ASC NULLS LAST, student_count DESC
                    LIMIT %s
                    """,
                    (class_id, course_id, _limit(top_k)),
                )
                return _result(tool, [dict(row) for row in cur.fetchall()])
        finally:
            conn.close()
    except Exception as exc:
        return _error(tool, str(exc))


@ToolRegistry.register(
    name="teacher_query_difficult_knowledge",
    description="查询当前班级在当前学科中错误次数最多的知识点和受影响学生数。",
    parameters={
        "type": "object",
        "properties": {
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
)
async def query_difficult_knowledge(user_id: int, top_k: int = 10) -> str:
    tool = "teacher_query_difficult_knowledge"
    try:
        teacher_id, class_id, course_id = _context_scope()
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _check_scope(cur, teacher_id, class_id, course_id)
                cur.execute(
                    """
                    SELECT
                        COALESCE(NULLIF(TRIM(er.kg_node_name), ''),
                                 NULLIF(TRIM(q.kg_node_name), '')) AS knowledge_name,
                        COUNT(*) AS wrong_count,
                        COUNT(DISTINCT er.stu_id) AS affected_student_count
                    FROM exercise_records er
                    JOIN students s ON s.stu_id = er.stu_id
                    JOIN questions q ON q.question_id = er.question_id
                    WHERE s.class_id = %s
                      AND er.course_id = %s
                      AND (er.do_istrue IS FALSE OR er.do_score < 6)
                      AND COALESCE(NULLIF(TRIM(er.kg_node_name), ''),
                                   NULLIF(TRIM(q.kg_node_name), '')) IS NOT NULL
                    GROUP BY knowledge_name
                    ORDER BY wrong_count DESC, affected_student_count DESC
                    LIMIT %s
                    """,
                    (class_id, course_id, _limit(top_k)),
                )
                return _result(tool, [dict(row) for row in cur.fetchall()])
        finally:
            conn.close()
    except Exception as exc:
        return _error(tool, str(exc))


@ToolRegistry.register(
    name="teacher_query_student_risk",
    description="查询当前班级在当前学科下需要重点关注的学生，综合学习进度、掌握度和错题数量排序。",
    parameters={
        "type": "object",
        "properties": {
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
)
async def query_student_risk(user_id: int, top_k: int = 10) -> str:
    tool = "teacher_query_student_risk"
    try:
        teacher_id, class_id, course_id = _context_scope()
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _check_scope(cur, teacher_id, class_id, course_id)
                cur.execute(
                    """
                    SELECT
                        s.stu_id,
                        s.stu_name,
                        s.stu_level,
                        scm.course_process,
                        scm.course_degree,
                        COUNT(er.do_id) FILTER (
                            WHERE er.do_istrue IS FALSE OR er.do_score < 6
                        ) AS wrong_count,
                        COUNT(er.do_id) AS exercise_count
                    FROM students s
                    LEFT JOIN student_course_mastery scm
                        ON scm.stu_id = s.stu_id AND scm.course_id = %s
                    LEFT JOIN exercise_records er
                        ON er.stu_id = s.stu_id AND er.course_id = %s
                    WHERE s.class_id = %s
                    GROUP BY s.stu_id, s.stu_name, s.stu_level,
                             scm.course_process, scm.course_degree
                    ORDER BY scm.course_process ASC NULLS FIRST,
                             scm.course_degree ASC NULLS FIRST,
                             wrong_count DESC
                    LIMIT %s
                    """,
                    (course_id, course_id, class_id, _limit(top_k)),
                )
                return _result(tool, [dict(row) for row in cur.fetchall()])
        finally:
            conn.close()
    except Exception as exc:
        return _error(tool, str(exc))


@ToolRegistry.register(
    name="teacher_query_student_profile",
    description="查询当前班级内指定学生在当前学科的学习进度、掌握度、错题数量和最近评价。",
    parameters={
        "type": "object",
        "properties": {
            "student_id": {"type": "integer", "minimum": 1},
        },
        "required": ["student_id"],
        "additionalProperties": False,
    },
)
async def query_student_profile(user_id: int, student_id: int) -> str:
    tool = "teacher_query_student_profile"
    try:
        teacher_id, class_id, course_id = _context_scope()
        conn = _get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _check_scope(cur, teacher_id, class_id, course_id)
                cur.execute(
                    """
                    SELECT
                        s.stu_id,
                        s.stu_name,
                        s.stu_level,
                        s.class_id,
                        scm.course_process,
                        scm.course_degree,
                        COUNT(er.do_id) FILTER (
                            WHERE er.do_istrue IS FALSE OR er.do_score < 6
                        ) AS wrong_count,
                        COUNT(er.do_id) AS exercise_count
                    FROM students s
                    LEFT JOIN student_course_mastery scm
                        ON scm.stu_id = s.stu_id AND scm.course_id = %s
                    LEFT JOIN exercise_records er
                        ON er.stu_id = s.stu_id AND er.course_id = %s
                    WHERE s.stu_id = %s AND s.class_id = %s
                    GROUP BY s.stu_id, s.stu_name, s.stu_level, s.class_id,
                             scm.course_process, scm.course_degree
                    """,
                    (course_id, course_id, student_id, class_id),
                )
                row = cur.fetchone()
                if row is None:
                    return _error(tool, "Student is not in the authorized class")

                cur.execute(
                    """
                    SELECT publisher_name, ea_description, updated_at
                    FROM evaluation_analysis
                    WHERE stu_id = %s
                    ORDER BY updated_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    (student_id,),
                )
                evaluation = cur.fetchone()
                data = dict(row)
                data["latest_evaluation"] = dict(evaluation) if evaluation else None
                return _result(tool, data)
        finally:
            conn.close()
    except Exception as exc:
        return _error(tool, str(exc))
