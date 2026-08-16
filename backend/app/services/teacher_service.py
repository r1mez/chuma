"""teacher service."""
import logging
from typing import List

import httpx
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.classes import Class
from app.models.course import Course
from app.models.exercise_record import ExerciseRecord
from app.models.kg_graph import KgGraph
from app.models.learning import StudentCourseMastery
from app.models.question import Question
from app.models.teacher_relation import TeacherClass, TeacherCourse
from app.models.user import Student
from app.services.mastery_service import MasteryService

logger = logging.getLogger(__name__)


class TeacherService:
    """Teacher-side business logic."""

    async def _teacher_has_access_to_class_and_course(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> bool:
        """Validate teacher-class-course ownership."""
        class_result = await db.execute(
            select(TeacherClass.class_id).where(
                TeacherClass.tea_id == tea_id,
                TeacherClass.class_id == class_id,
            )
        )
        if class_result.first() is None:
            return False

        course_result = await db.execute(
            select(TeacherCourse.course_id).where(
                TeacherCourse.tea_id == tea_id,
                TeacherCourse.course_id == course_id,
            )
        )
        return course_result.first() is not None

    async def get_teacher_courses(self, tea_id: int, db: AsyncSession) -> List[dict]:
        """Return the course list taught by the teacher."""
        stmt = (
            select(Course.course_id, Course.course_name)
            .join(TeacherCourse, TeacherCourse.course_id == Course.course_id)
            .where(TeacherCourse.tea_id == tea_id)
            .order_by(Course.course_id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"course_id": course_id, "course_name": course_name}
            for course_id, course_name in rows
        ]

    async def get_course_chapters(
        self, tea_id: int, course_id: int, db: AsyncSession
    ) -> List[dict]:
        """返回某学科知识图谱中的章节列表。

        数据对应关系（严格遵循建表脚本）：
          teacher_course(tea_id, course_id) 校验教师-学科归属
          courses.course_id -> courses.kg_id -> kg_graphs.graph_name
          通过 AI 引擎 /kg/graph/data 查询该图，筛选 type == 'Chapter' 的节点。
        """
        # 1. 校验教师确实教授该学科
        course_result = await db.execute(
            select(TeacherCourse.course_id).where(
                TeacherCourse.tea_id == tea_id,
                TeacherCourse.course_id == course_id,
            )
        )
        if course_result.first() is None:
            return []

        # 2. 获取学科对应的知识图谱 graph_name
        kg_result = await db.execute(
            select(Course.kg_id)
            .where(Course.course_id == course_id)
        )
        kg_id = kg_result.scalar_one_or_none()
        if kg_id is None:
            return []

        graph_result = await db.execute(
            select(KgGraph.graph_name).where(KgGraph.id == kg_id)
        )
        graph_name = graph_result.scalar_one_or_none()
        if not graph_name:
            return []

        # 3. 通过 AI 引擎查询图数据，筛选章节节点
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/kg/graph/data",
                    params={"graph_name": graph_name},
                    headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"KG graph data request failed for {graph_name}: {response.status_code}"
                    )
                    return []
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"KG graph data request error: {e}")
            return []

        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        chapters = [
            {
                "name": node.get("name") or node.get("id"),
                "id": node.get("id"),
            }
            for node in nodes
            if (node.get("type") or "").lower() == "chapter"
        ]
        # 按名称排序，保证展示稳定
        chapters.sort(key=lambda item: item["name"] or "")
        return chapters

    async def get_course_sections(
        self, tea_id: int, course_id: int, db: AsyncSession
    ) -> List[dict]:
        """Return every selectable chapter/subsection in a teacher-owned KG.

        A KG represents both chapters and subsections as ``Chapter`` nodes.  The
        containment edge provides the hierarchy, so this method turns the flat
        graph into stable labelled options for the lesson-plan creator.
        """
        course_result = await db.execute(
            select(TeacherCourse.course_id).where(
                TeacherCourse.tea_id == tea_id,
                TeacherCourse.course_id == course_id,
            )
        )
        if course_result.first() is None:
            return []

        kg_result = await db.execute(
            select(Course.kg_id).where(Course.course_id == course_id)
        )
        kg_id = kg_result.scalar_one_or_none()
        if kg_id is None:
            return []
        graph_result = await db.execute(
            select(KgGraph.graph_name).where(KgGraph.id == kg_id)
        )
        graph_name = graph_result.scalar_one_or_none()
        if not graph_name:
            return []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/kg/graph/data",
                    params={"graph_name": graph_name},
                    headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("KG section request failed for course %s: %s", course_id, exc)
            return []

        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        edges = data.get("edges", []) if isinstance(data, dict) else []
        node_map = {
            str(node.get("id")): node
            for node in nodes
            if node.get("id") is not None
        }
        section_ids = {
            node_id
            for node_id, node in node_map.items()
            if str(node.get("type", "")).strip().lower() in {"chapter", "章节"}
        }
        if not section_ids:
            return []

        parent_by_child: dict[str, str] = {}
        contains_names = {"包含", "contains", "contain", "includes", "include"}
        for edge in edges:
            relation = str(edge.get("relationship_name", "")).strip().lower()
            source_id = str(edge.get("source", ""))
            target_id = str(edge.get("target", ""))
            if relation in contains_names and source_id in section_ids and target_id in section_ids:
                parent_by_child.setdefault(target_id, source_id)

        def section_path(section_id: str, seen: set[str] | None = None) -> list[str]:
            seen = set() if seen is None else seen
            if section_id in seen:
                return []
            seen.add(section_id)
            node = node_map.get(section_id, {})
            name = str(node.get("name") or section_id)
            parent_id = parent_by_child.get(section_id)
            return ([*section_path(parent_id, seen), name] if parent_id else [name])

        sections = []
        for section_id in section_ids:
            node = node_map[section_id]
            path = section_path(section_id)
            sections.append(
                {
                    "id": section_id,
                    "name": str(node.get("name") or section_id),
                    "type": str(node.get("type") or "Chapter"),
                    "path": " / ".join(path),
                    "parent_id": parent_by_child.get(section_id),
                    "description": str(node.get("description") or ""),
                }
            )
        return sorted(sections, key=lambda item: (item["path"], item["id"]))

    async def get_teacher_classes(self, tea_id: int, db: AsyncSession) -> List[dict]:
        """Return the class list managed by the teacher."""
        stmt = (
            select(
                Class.class_id,
                Class.class_name,
                Class.classmates_num,
                func.count(Student.stu_id).label("student_count"),
            )
            .join(TeacherClass, TeacherClass.class_id == Class.class_id)
            .outerjoin(Student, Student.class_id == Class.class_id)
            .where(TeacherClass.tea_id == tea_id)
            .group_by(Class.class_id, Class.class_name, Class.classmates_num)
            .order_by(Class.class_id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "class_id": class_id,
                "class_name": class_name,
                "classmates_num": classmates_num,
                "student_count": student_count,
            }
            for class_id, class_name, classmates_num, student_count in rows
        ]

    async def get_class_students(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> List[dict]:
        """Return students in the class with progress for the selected course."""
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id, course_id, db
        ):
            return []

        stmt = (
            select(
                Student.stu_id,
                Student.stu_name,
                Student.stu_level,
                StudentCourseMastery.course_process,
            )
            .outerjoin(
                StudentCourseMastery,
                (StudentCourseMastery.stu_id == Student.stu_id)
                & (StudentCourseMastery.course_id == course_id),
            )
            .where(Student.class_id == class_id)
            .order_by(Student.stu_id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "stu_id": stu_id,
                "stu_name": stu_name,
                "stu_level": stu_level,
                "course_process": course_process,
            }
            for stu_id, stu_name, stu_level, course_process in rows
        ]

    async def get_class_summary(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> dict:
        """Return real KPI values for the teacher class dashboard.

        There is currently no assignment-batch table, so the score KPI is
        calculated from each student's latest submitted question in the
        selected course. Objective answers are normalized to 0/100 and
        subjective scores (stored on a 0-10 scale) are normalized to 0/100.
        """
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id, course_id, db
        ):
            return {
                "status": "no_access",
                "class_id": class_id,
                "course_id": course_id,
            }

        student_count_result = await db.execute(
            select(func.count(Student.stu_id)).where(Student.class_id == class_id)
        )
        student_count = int(student_count_result.scalar_one() or 0)

        mastery_result = await db.execute(
            select(
                func.avg(StudentCourseMastery.course_process),
                func.count(StudentCourseMastery.stu_id),
            )
            .join(Student, Student.stu_id == StudentCourseMastery.stu_id)
            .where(
                Student.class_id == class_id,
                StudentCourseMastery.course_id == course_id,
                StudentCourseMastery.course_process.isnot(None),
            )
        )
        average_mastery, mastery_sample_count = mastery_result.one()

        # Use the latest record per student, rather than averaging repeated
        # retries from the same student.
        latest_record_ids = (
            select(func.max(ExerciseRecord.do_id).label("latest_do_id"))
            .join(Student, Student.stu_id == ExerciseRecord.stu_id)
            .where(
                Student.class_id == class_id,
                ExerciseRecord.course_id == course_id,
            )
            .group_by(ExerciseRecord.stu_id)
        )
        normalized_score = case(
            (ExerciseRecord.do_score.isnot(None), ExerciseRecord.do_score * 10.0),
            (ExerciseRecord.do_isTrue.is_(True), 100.0),
            (ExerciseRecord.do_isTrue.is_(False), 0.0),
            else_=None,
        )
        score_result = await db.execute(
            select(func.avg(normalized_score), func.count(ExerciseRecord.do_id)).where(
                ExerciseRecord.do_id.in_(latest_record_ids)
            )
        )
        latest_average_score, score_sample_count = score_result.one()

        level_result = await db.execute(
            select(Student.stu_level).where(
                Student.class_id == class_id,
                Student.stu_level.isnot(None),
            )
        )
        level_points = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
        rated_levels = [
            level_points[str(level).strip().upper()]
            for level in level_result.scalars().all()
            if str(level).strip().upper() in level_points
        ]
        rating_average = (
            sum(rated_levels) / len(rated_levels) if rated_levels else None
        )
        class_rating = None
        if rating_average is not None:
            class_rating = (
                "A" if rating_average >= 4.5
                else "B" if rating_average >= 3.5
                else "C" if rating_average >= 2.5
                else "D" if rating_average >= 1.5
                else "E"
            )

        return {
            "status": "ok",
            "class_id": class_id,
            "course_id": course_id,
            "student_count": student_count,
            "class_rating": class_rating,
            "latest_average_score": (
                round(float(latest_average_score), 1)
                if latest_average_score is not None
                else None
            ),
            "average_mastery": (
                round(float(average_mastery), 4)
                if average_mastery is not None
                else None
            ),
            "rated_student_count": len(rated_levels),
            "score_sample_count": int(score_sample_count or 0),
            "mastery_sample_count": int(mastery_sample_count or 0),
        }

    async def get_difficult_knowledge_points(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> List[dict]:
        """Return top difficult knowledge points for the class/course word cloud."""
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id, course_id, db
        ):
            return []

        knowledge_name = func.coalesce(
            func.nullif(func.trim(ExerciseRecord.kg_node_name), ""),
            func.nullif(func.trim(Question.kg_node_name), ""),
        )
        stmt = (
            select(
                knowledge_name.label("knowledge_name"),
                func.count(ExerciseRecord.do_id).label("count"),
            )
            .join(Student, Student.stu_id == ExerciseRecord.stu_id)
            .join(Question, Question.question_id == ExerciseRecord.question_id)
            .where(
                Student.class_id == class_id,
                ExerciseRecord.course_id == course_id,
                ExerciseRecord.do_isTrue.is_(False),
                knowledge_name.isnot(None),
            )
            .group_by(knowledge_name)
        )
        result = await db.execute(stmt)
        rows = result.all()

        total_count = sum(count for _, count in rows)
        if total_count == 0:
            return []

        items = [
            {
                "name": name,
                "count": count,
                "ratio": round(count / total_count, 4),
            }
            for name, count in rows
        ]
        items.sort(key=lambda item: (-item["count"], item["name"]))
        return items[:20]

    async def get_difficult_chapters(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> List[dict]:
        """返回该班级该学科下所有学生错题知识点归类到顶层章节后的疑难章节分布。

        归类规则（严格遵循知识图谱分层结构）：
          - 章节(Chapter)节点通过「包含」边形成层级：章节 -> 小节 -> 知识点
          - 非 Chapter 节点视为知识点，挂载到其所属章节下
          - 当某小节(Chapter)下没有知识点时，该小节本身视为知识点
          - 所有错题知识点最终向上归类到其所属的顶层章节
        返回各顶层章节的错题知识点数量与占比，用于疑难章节饼状图。
        """
        # 1. 校验教师-班级-学科归属
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id, course_id, db
        ):
            return []

        # 2. 统计该班级该学科下所有学生的错题知识点数量
        knowledge_name = func.coalesce(
            func.nullif(func.trim(ExerciseRecord.kg_node_name), ""),
            func.nullif(func.trim(Question.kg_node_name), ""),
        )
        stmt = (
            select(
                knowledge_name.label("knowledge_name"),
                func.count(ExerciseRecord.do_id).label("count"),
            )
            .join(Student, Student.stu_id == ExerciseRecord.stu_id)
            .join(Question, Question.question_id == ExerciseRecord.question_id)
            .where(
                Student.class_id == class_id,
                ExerciseRecord.course_id == course_id,
                ExerciseRecord.do_isTrue.is_(False),
                knowledge_name.isnot(None),
            )
            .group_by(knowledge_name)
        )
        result = await db.execute(stmt)
        rows = result.all()
        if not rows:
            return []

        # 3. 获取该学科知识图谱全量数据（节点 + 边）
        kg_result = await db.execute(
            select(Course.kg_id).where(Course.course_id == course_id)
        )
        kg_id = kg_result.scalar_one_or_none()
        if kg_id is None:
            return []
        graph_result = await db.execute(
            select(KgGraph.graph_name).where(KgGraph.id == kg_id)
        )
        graph_name = graph_result.scalar_one_or_none()
        if not graph_name:
            return []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/kg/graph/data",
                    params={"graph_name": graph_name},
                    headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"KG graph data request failed for {graph_name}: {response.status_code}"
                    )
                    return []
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"KG graph data request error: {e}")
            return []

        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        edges = data.get("edges", []) if isinstance(data, dict) else []

        # 4. 构建章节层级结构
        node_map = {}
        for node in nodes:
            node_id = node.get("id")
            if node_id is not None:
                node_map[node_id] = node

        # 章节父子关系：Chapter -> Chapter（「包含」边）
        chapter_children = {}  # parent_id -> [child_id]
        # 知识点归属：Chapter -> [知识点节点 id]
        chapter_knowledge_points = {}  # chapter_id -> [kp_id]
        for edge in edges:
            rel = (edge.get("relationship_name") or "").strip()
            if rel != "包含":
                continue
            src = edge.get("source")
            tgt = edge.get("target")
            src_node = node_map.get(src)
            tgt_node = node_map.get(tgt)
            if src_node is None or tgt_node is None:
                continue
            src_is_chapter = (src_node.get("type") or "").lower() == "chapter"
            tgt_is_chapter = (tgt_node.get("type") or "").lower() == "chapter"
            if src_is_chapter and tgt_is_chapter:
                chapter_children.setdefault(src, []).append(tgt)
            elif src_is_chapter and not tgt_is_chapter:
                chapter_knowledge_points.setdefault(src, []).append(tgt)

        # 5. 将错题知识点归类到顶层章节
        # 建立「知识点节点 id -> 所属顶层章节 id」的映射
        kp_to_top = {}

        def resolve_top(chapter_id: int, visited: set) -> int:
            """沿章节父子链向上找到顶层章节。"""
            if chapter_id in visited:
                return chapter_id
            visited.add(chapter_id)
            for parent_id, children in chapter_children.items():
                if chapter_id in children:
                    return resolve_top(parent_id, visited)
            return chapter_id

        # 知识点节点 -> 所属章节 -> 顶层章节
        for chapter_id, kp_ids in chapter_knowledge_points.items():
            top_id = resolve_top(chapter_id, set())
            for kp_id in kp_ids:
                kp_to_top[kp_id] = top_id

        # 章节归类统计
        chapter_count = {}  # top_chapter_id -> count
        for name, count in rows:
            # 按名称在节点中查找（可能多个同名节点，取第一个）
            matched = None
            for node in nodes:
                if (node.get("name") or node.get("id")) == name:
                    matched = node
                    break
            if matched is None:
                continue
            node_id = matched.get("id")
            node_type = (matched.get("type") or "").lower()
            if node_type == "chapter":
                # 小节本身视为知识点：无论其下是否挂有知识点，错题记录指向章节本身时，
                # 一律向上归类到该章节所属的顶层章节
                top_id = resolve_top(node_id, set())
            else:
                top_id = kp_to_top.get(node_id)
                if top_id is None:
                    continue
            chapter_count[top_id] = chapter_count.get(top_id, 0) + count

        if not chapter_count:
            return []

        total_count = sum(chapter_count.values())
        items = [
            {
                "name": node_map.get(chapter_id, {}).get("name")
                or node_map.get(chapter_id, {}).get("id"),
                "count": count,
                "ratio": round(count / total_count, 4),
            }
            for chapter_id, count in chapter_count.items()
        ]
        items.sort(key=lambda item: (-item["count"], item["name"] or ""))
        return items

    async def get_class_teaching_suggestion(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> dict:
        """生成班级教学建议（调用 AI 引擎的 ReAct Agent）。

        综合三个维度（学生评级、班级知识点平均掌握度进度、疑难章节与知识点），
        各维度等权（3 维各 1/3，2 维各 1/2），缺失维度时触发兜底机制。

        返回结构（与 AI 引擎 /analysis/class_teaching_suggestion 一致）：
          {
            "class_id", "course_id", "course_name",
            "status": "ok" | "insufficient" | "db_error",
            "dimensions_available", "weights", "dimensions_detail",
            "missing_dimensions", "error", "error_message", "suggestion"
          }
        """
        # 1. 校验教师-班级-学科归属
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id, course_id, db
        ):
            return {
                "class_id": class_id,
                "course_id": course_id,
                "course_name": None,
                "status": "db_error",
                "dimensions_available": 0,
                "weights": {},
                "dimensions_detail": {},
                "missing_dimensions": [],
                "error": "no_access",
                "error_message": "您无权访问该班级或该学科的教学数据。",
                "suggestion": None,
            }

        # 2. 获取学科名称
        course_result = await db.execute(
            select(Course.course_name).where(Course.course_id == course_id)
        )
        course_name = course_result.scalar_one_or_none()

        # 3. 调用 AI 引擎生成教学建议
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.AI_SERVICE_URL}/analysis/class_teaching_suggestion",
                    params={
                        "class_id": class_id,
                        "course_id": course_id,
                        "course_name": course_name,
                    },
                    headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"Class teaching suggestion request failed: "
                        f"class_id={class_id}, course_id={course_id}, "
                        f"status={response.status_code}"
                    )
                    return {
                        "class_id": class_id,
                        "course_id": course_id,
                        "course_name": course_name,
                        "status": "db_error",
                        "dimensions_available": 0,
                        "weights": {},
                        "dimensions_detail": {},
                        "missing_dimensions": [],
                        "error": "ai_error",
                        "error_message": "AI 教学建议服务暂时不可用，请稍后重试。",
                        "suggestion": None,
                    }
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Class teaching suggestion request error: {e}")
            return {
                "class_id": class_id,
                "course_id": course_id,
                "course_name": course_name,
                "status": "db_error",
                "dimensions_available": 0,
                "weights": {},
                "dimensions_detail": {},
                "missing_dimensions": [],
                "error": "ai_error",
                "error_message": "AI 教学建议服务暂时不可用，请稍后重试。",
                "suggestion": None,
            }

    async def get_student_knowledge_graph(
        self, tea_id: int, student_id: int, course_id: int, db: AsyncSession
    ) -> dict:
        """返回某学生在某学科下的个人知识图谱（图数据 + 掌握度层级树）。

        严格对应关系（遵循建表脚本）：
          - teacher_class(tea_id, class_id)  校验教师-班级归属
          - teacher_course(tea_id, course_id) 校验教师-学科归属
          - students.class_id == class_id     校验学生-班级归属
        三者同时满足，教师才能查看该学生的知识图谱，否则返回空结果。

        返回结构：
          {
            "graph": { nodes, edges, stats },   # 该学科知识图谱全量数据
            "mastery": { course_id, course_name, course_degree,
                         course_process, chapters }  # 该学生掌握度层级树
          }
        """
        # 1. 校验学生存在及其所属班级
        student_result = await db.execute(
            select(Student.stu_id, Student.class_id).where(
                Student.stu_id == student_id
            )
        )
        student_row = student_result.first()
        if student_row is None:
            return {}
        stu_id, stu_class_id = student_row
        if stu_class_id is None:
            return {}

        # 2. 严格校验教师-班级-学科归属：教师必须同时教授该学生所在班级与该学科
        if not await self._teacher_has_access_to_class_and_course(
            tea_id, class_id=stu_class_id, course_id=course_id, db=db
        ):
            return {}

        # 3. 获取该学科知识图谱 graph_name
        kg_result = await db.execute(
            select(Course.kg_id).where(Course.course_id == course_id)
        )
        kg_id = kg_result.scalar_one_or_none()
        if kg_id is None:
            return {}
        graph_result = await db.execute(
            select(KgGraph.graph_name).where(KgGraph.id == kg_id)
        )
        graph_name = graph_result.scalar_one_or_none()
        if not graph_name:
            return {}

        # 4. 通过 AI 引擎查询图数据
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/kg/graph/data",
                    params={"graph_name": graph_name},
                    headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                )
                if response.status_code >= 400:
                    logger.warning(
                        f"KG graph data request failed for {graph_name}: {response.status_code}"
                    )
                    return {}
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"KG graph data request error: {e}")
            return {}

        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        edges = data.get("edges", []) if isinstance(data, dict) else []
        if not nodes:
            return {}

        # 5. 计算该学生的掌握度层级树
        mastery_service = MasteryService()
        mastery = await mastery_service.get_mastery_hierarchy(stu_id, course_id, db)

        # 6. 组装图数据统计
        type_counter: dict = {}
        for node in nodes:
            node_type = node.get("type") or "unknown"
            type_counter[node_type] = type_counter.get(node_type, 0) + 1

        return {
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "node_types": type_counter,
                },
            },
            "mastery": mastery,
        }
