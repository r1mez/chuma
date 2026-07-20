"""Auth 业务逻辑层"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import Student, Teacher
from app.schemas.auth import (
    StudentRegisterRequest, TeacherRegisterRequest,
    StudentResponse, TeacherResponse, TokenResponse,
)


class AuthService:
    async def register_student(self, data: StudentRegisterRequest, db: AsyncSession) -> StudentResponse:
        hashed = hash_password(data.stu_pwd) if data.stu_pwd else None
        student = Student(
            stu_name=data.stu_name,
            stu_email=data.stu_email,
            stu_pwd=hashed,
            stu_gender=data.stu_gender,
        )
        db.add(student)
        await db.commit()
        await db.refresh(student)
        return StudentResponse.model_validate(student)

    async def register_teacher(self, data: TeacherRegisterRequest, db: AsyncSession) -> TeacherResponse:
        hashed = hash_password(data.tea_pwd) if data.tea_pwd else None
        teacher = Teacher(
            tea_name=data.tea_name,
            tea_email=data.tea_email,
            tea_pwd=hashed,
        )
        db.add(teacher)
        await db.commit()
        await db.refresh(teacher)
        return TeacherResponse.model_validate(teacher)

    async def login(self, email: str, password: str, user_type: str, db: AsyncSession) -> Optional[TokenResponse]:
        if user_type == "student":
            result = await db.execute(select(Student).where(Student.stu_email == email))
            user = result.scalar_one_or_none()
            user_id = user.stu_id if user else None
            stored_hash = user.stu_pwd if user else None
        elif user_type == "teacher":
            result = await db.execute(select(Teacher).where(Teacher.tea_email == email))
            user = result.scalar_one_or_none()
            user_id = user.tea_id if user else None
            stored_hash = user.tea_pwd if user else None
        else:
            return None
        if user is None or stored_hash is None:
            return None
        if not verify_password(password, stored_hash):
            return None
        token = create_access_token(data={"sub": str(user_id), "user_type": user_type})
        return TokenResponse(access_token=token, user_type=user_type, user_id=user_id)

    async def get_student_by_id(self, stu_id: int, db: AsyncSession) -> Optional[StudentResponse]:
        result = await db.execute(select(Student).where(Student.stu_id == stu_id))
        student = result.scalar_one_or_none()
        if student is None:
            return None
        return StudentResponse.model_validate(student)

    async def get_teacher_by_id(self, tea_id: int, db: AsyncSession) -> Optional[TeacherResponse]:
        result = await db.execute(select(Teacher).where(Teacher.tea_id == tea_id))
        teacher = result.scalar_one_or_none()
        if teacher is None:
            return None
        return TeacherResponse.model_validate(teacher)
