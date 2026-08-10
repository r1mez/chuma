"""Student-scoped tools for the conversational tutor.

These tools deliberately derive the student identity from ``AgentContext``.
The model may narrow a query by course, but can never choose another student.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

from app.agent.context import current_agent_context
from app.agent.tool_registry import ToolRegistry
from app.config import settings

logger = logging.getLogger(__name__)


def _student_scope() -> int:
    context = current_agent_context.get()
    if context is None:
        raise PermissionError("Student tools require an AgentContext")
    if context.student_id is not None:
        return context.student_id
    if context.user_role == "student":
        return context.user_id
    raise PermissionError("A student scope is required for this tool")


def _course_scope(course_id: int | None) -> int | None:
    context = current_agent_context.get()
    if context is not None and context.course_id is not None:
        if course_id is not None and course_id != context.course_id:
            raise PermissionError("The requested course is outside the current scope")
        return context.course_id
    return course_id


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


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _success(tool: str, data: Any, summary: str) -> str:
    return json.dumps(
        {"tool": tool, "success": True, "data": _json_safe(data), "summary": summary},
        ensure_ascii=False,
    )


def _failure(tool: str, message: str) -> str:
    logger.warning("%s failed: %s", tool, message)
    return json.dumps(
        {"tool": tool, "success": False, "data": None, "summary": message},
        ensure_ascii=False,
    )


@ToolRegistry.register(
    name="query_my_mastery",
    description="查询当前学生自己的知识点掌握度，可按学科筛选，返回掌握度最低的知识点优先列表。",
    parameters={
        "type": "object",
        "properties": {
            "course_id": {"type": "integer", "minimum": 1, "description": "可选学科 ID"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
    display_name="查询我的知识掌握度",
    purpose="定位当前学生的薄弱知识点",
)
async def query_my_mastery(
    user_id: int,
    course_id: int | None = None,
    top_k: int = 10,
) -> str:
    tool = "query_my_mastery"
    conn = None
    try:
        stu_id = _student_scope()
        course_id = _course_scope(course_id)
        top_k = max(1, min(int(top_k), 20))
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if course_id is None:
                cur.execute(
                    """
                    SELECT skm.course_id, c.course_name, skm.kg_node_name,
                           skm.kg_degree, skm.answered_count, skm.correct_count
                    FROM student_knowledge_mastery skm
                    LEFT JOIN courses c ON c.course_id = skm.course_id
                    WHERE skm.stu_id = %s
                    ORDER BY skm.kg_degree ASC NULLS FIRST, skm.updated_at DESC
                    LIMIT %s
                    """,
                    (stu_id, top_k),
                )
            else:
                cur.execute(
                    """
                    SELECT skm.course_id, c.course_name, skm.kg_node_name,
                           skm.kg_degree, skm.answered_count, skm.correct_count
                    FROM student_knowledge_mastery skm
                    LEFT JOIN courses c ON c.course_id = skm.course_id
                    WHERE skm.stu_id = %s AND skm.course_id = %s
                    ORDER BY skm.kg_degree ASC NULLS FIRST, skm.updated_at DESC
                    LIMIT %s
                    """,
                    (stu_id, course_id, top_k),
                )
            rows = [dict(row) for row in cur.fetchall()]
        if not rows:
            return _failure(tool, "暂未找到你的知识点掌握度记录。")
        return _success(
            tool,
            {"student_id": stu_id, "items": rows},
            f"已查询到你的 {len(rows)} 条知识点掌握度记录，结果按掌握度从低到高排列。",
        )
    except Exception as exc:
        return _failure(tool, f"查询你的知识掌握度失败：{exc}")
    finally:
        if conn is not None:
            conn.close()


@ToolRegistry.register(
    name="query_my_exercises",
    description="查询当前学生自己的做题记录，可筛选某个学科或只看错题，不返回其他学生数据。",
    parameters={
        "type": "object",
        "properties": {
            "course_id": {"type": "integer", "minimum": 1, "description": "可选学科 ID"},
            "wrong_only": {"type": "boolean", "description": "是否只查询错题"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
    display_name="查询我的做题记录",
    purpose="了解自己的练习表现和错题情况",
)
async def query_my_exercises(
    user_id: int,
    course_id: int | None = None,
    wrong_only: bool = False,
    top_k: int = 10,
) -> str:
    tool = "query_my_exercises"
    conn = None
    try:
        stu_id = _student_scope()
        course_id = _course_scope(course_id)
        top_k = max(1, min(int(top_k), 20))
        conn = _get_conn()
        clauses = ["er.stu_id = %s"]
        params: list[Any] = [stu_id]
        if course_id is not None:
            clauses.append("er.course_id = %s")
            params.append(course_id)
        if wrong_only:
            clauses.append("(er.do_istrue IS FALSE OR er.do_score < 6)")
        params.append(top_k)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT er.question_id, er.course_id, c.course_name,
                       COALESCE(er.kg_node_name, q.kg_node_name) AS kg_node_name,
                       er.question_type, er.question_difficulty, er.do_score,
                       er.do_istrue, er.created_at, q.question_description
                FROM exercise_records er
                LEFT JOIN questions q ON q.question_id = er.question_id
                LEFT JOIN courses c ON c.course_id = er.course_id
                WHERE {' AND '.join(clauses)}
                ORDER BY er.created_at DESC NULLS LAST
                LIMIT %s
                """,
                tuple(params),
            )
            rows = [dict(row) for row in cur.fetchall()]
        if not rows:
            return _failure(tool, "暂未找到你的做题记录。")
        return _success(
            tool,
            {"student_id": stu_id, "items": rows},
            f"已查询到你的 {len(rows)} 条做题记录。",
        )
    except Exception as exc:
        return _failure(tool, f"查询你的做题记录失败：{exc}")
    finally:
        if conn is not None:
            conn.close()


@ToolRegistry.register(
    name="socratic_hint",
    description="为当前学生提供分阶段的苏格拉底式解题提示，不直接给出答案；只有读题至少一分钟后才允许请求。",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1, "description": "题目内容"},
            "student_attempt": {"type": "string", "description": "学生已经尝试的思路，可选"},
            "elapsed_seconds": {"type": "integer", "minimum": 0, "description": "学生读题经过的秒数"},
            "hint_level": {"type": "integer", "minimum": 1, "maximum": 3},
        },
        "required": ["question", "elapsed_seconds"],
        "additionalProperties": False,
    },
    display_name="获取苏格拉底式提示",
    purpose="在不直接泄露答案的情况下帮助学生形成解题思路",
)
async def socratic_hint(
    user_id: int,
    question: str,
    elapsed_seconds: int,
    student_attempt: str = "",
    hint_level: int = 1,
) -> str:
    tool = "socratic_hint"
    try:
        _student_scope()
        if int(elapsed_seconds) < 60:
            remaining = 60 - int(elapsed_seconds)
            return _failure(tool, f"请先独立读题，{remaining} 秒后再请求提示。")
        level = max(1, min(int(hint_level), 3))
        prompts = {
            1: "先复述题目要求，并指出题目涉及的核心概念或数据结构。",
            2: "检查你的思路中每一步的输入、输出和成立条件；哪一步最需要证明？",
            3: "尝试构造一个最小例子或反例，验证当前思路是否能覆盖边界情况。",
        }
        data = {
            "hint_level": level,
            "question_length": len(question.strip()),
            "student_attempt_provided": bool(student_attempt.strip()),
            "next_question": prompts[level],
            "rule": "提示只引导思考，不直接给出最终答案。",
        }
        return _success(tool, data, prompts[level])
    except Exception as exc:
        return _failure(tool, f"生成解题提示失败：{exc}")
