"""teacher 业务逻辑层"""
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.classes import Class
from app.models.user import Student
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
