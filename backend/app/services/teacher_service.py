"""teacher 业务逻辑层"""
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.classes import Class
from app.models.user import Student
from app.models.learning import StudentCourseMastery
from app.models.teacher_relation import TeacherCourse, TeacherClass


class TeacherService:
    """教师端业务逻辑"""

    async def get_teacher_courses(self, tea_id: int, db: AsyncSession) -> List[dict]:
        """获取教师所授学科列表（通过 teacher_course 关联表）"""
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
        """获取教师所管班级列表（通过 teacher_class 关联表），并统计各班学生数量"""
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
        """获取指定班级的学生列表，并关联所选学科的学习进度与评级。

        强逻辑保证一一对应：
        - 教师 -> 班级：通过 teacher_class 校验该教师确实管理该班级；
        - 班级 -> 学生：通过 students.class_id 取该班级学生；
        - 学生 + 学科 -> 进度：通过 student_course_mastery 按 (stu_id, course_id) 取 course_process；
        - 学生评级：取 students.stu_level。
        """
        # 1. 校验教师是否管理该班级
        owns = await db.execute(
            select(TeacherClass.class_id).where(
                TeacherClass.tea_id == tea_id,
                TeacherClass.class_id == class_id,
            )
        )
        if owns.first() is None:
            return []

        # 2. 查询该班级学生，并左连接所选学科的掌握度记录
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
