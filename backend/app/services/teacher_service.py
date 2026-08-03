"""teacher service."""
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classes import Class
from app.models.course import Course
from app.models.exercise_record import ExerciseRecord
from app.models.learning import StudentCourseMastery
from app.models.question import Question
from app.models.teacher_relation import TeacherClass, TeacherCourse
from app.models.user import Student


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
