"""Teacher lesson-plan job orchestration and AI-service reconciliation."""

from __future__ import annotations

import logging
import json
import secrets
from uuid import uuid4

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.classes import Class
from app.models.course import Course
from app.models.lesson_plan import LessonPlan
from app.schemas.lesson_plan import LessonPlanCreate
from app.services.teacher_service import TeacherService

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"queued", "generating"}
_ALL_STATUSES = _ACTIVE_STATUSES | {"completed", "failed"}
_PREVIEW_TICKET_TTL = 900


class LessonPlanService:
    """Keep authorization and durable metadata in backend; render in AI service."""

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"X-Service-Token": settings.AI_SERVICE_TOKEN}

    @staticmethod
    def _serialize(plan: LessonPlan, class_name: str | None = None, course_name: str | None = None) -> dict:
        return {
            "lesson_plan_id": plan.lesson_plan_id,
            "title": plan.title,
            "class_id": plan.class_id,
            "class_name": class_name,
            "course_id": plan.course_id,
            "course_name": course_name,
            "section_id": plan.section_id,
            "section_name": plan.section_name,
            "section_path": plan.section_path or plan.section_name,
            "previous_section_name": plan.previous_section_name,
            "include_review": bool(plan.include_review),
            "slide_count": plan.slide_count,
            "theme_pack": plan.theme_pack or "theme03",
            "task_id": plan.task_id,
            "status": plan.status,
            "content": plan.content if isinstance(plan.content, dict) else None,
            "file_name": plan.file_name,
            "error_message": plan.error_message,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    async def _load_names(self, plan: LessonPlan, db: AsyncSession) -> tuple[str | None, str | None]:
        result = await db.execute(
            select(Class.class_name, Course.course_name)
            .join(Course, Course.course_id == plan.course_id)
            .where(Class.class_id == plan.class_id)
        )
        row = result.first()
        return (row[0], row[1]) if row else (None, None)

    async def create(self, tea_id: int, data: LessonPlanCreate, db: AsyncSession) -> dict:
        teacher_service = TeacherService()
        if not await teacher_service._teacher_has_access_to_class_and_course(  # noqa: SLF001
            tea_id, data.class_id, data.course_id, db
        ):
            raise ValueError("无权为该班级和学科生成教案")

        sections = await teacher_service.get_course_sections(tea_id, data.course_id, db)
        selected_section = next((item for item in sections if item["id"] == data.section_id), None)
        if selected_section is None:
            raise ValueError("所选小节不存在，或不属于当前教师的学科图谱")

        course_result = await db.execute(
            select(Course.course_name, Course.kg_id).where(Course.course_id == data.course_id)
        )
        course_row = course_result.first()
        class_result = await db.execute(
            select(Class.class_name).where(Class.class_id == data.class_id)
        )
        class_name = class_result.scalar_one_or_none()
        if course_row is None or class_name is None:
            raise ValueError("班级或学科不存在")

        course_name, kg_graph_id = course_row
        siblings = sorted(
            [item for item in sections if item.get("parent_id") == selected_section.get("parent_id")],
            key=lambda item: (item.get("path", ""), item["id"]),
        )
        sibling_index = next((index for index, item in enumerate(siblings) if item["id"] == data.section_id), -1)
        previous = siblings[sibling_index - 1] if sibling_index > 0 else None

        task_id = uuid4().hex
        plan = LessonPlan(
            tea_id=tea_id,
            class_id=data.class_id,
            course_id=data.course_id,
            kg_graph_id=kg_graph_id,
            section_id=selected_section["id"],
            section_name=selected_section["name"],
            section_path=selected_section.get("path") or selected_section["name"],
            previous_section_name=previous["name"] if previous else None,
            include_review=data.include_review,
            slide_count=data.slide_count,
            theme_pack=data.theme_pack,
            title=f"{selected_section['name']} 教案",
            task_id=task_id,
            status="queued",
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        try:
            summary, difficult_knowledge, difficult_chapters = await self._class_context(
                teacher_service, tea_id, data.class_id, data.course_id, db
            )
            payload = {
                "task_id": task_id,
                "lesson_plan_id": plan.lesson_plan_id,
                "teacher_id": tea_id,
                "class_id": data.class_id,
                "class_name": class_name,
                "course_id": data.course_id,
                "course_name": course_name,
                "kg_graph_id": kg_graph_id,
                "section": selected_section,
                "previous_section": previous,
                "include_review": data.include_review,
                "slide_count": data.slide_count,
                "theme_pack": data.theme_pack,
                "class_summary": summary,
                "difficult_knowledge": difficult_knowledge,
                "difficult_chapters": difficult_chapters,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.AI_SERVICE_URL}/lesson-plans/submit",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Failed to submit lesson-plan task %s", task_id)
            plan.status = "failed"
            plan.error_message = "AI 教案任务提交失败，请检查 AI 服务后重试。"
            await db.commit()

        return self._serialize(plan, class_name=class_name, course_name=course_name)

    async def _class_context(
        self,
        teacher_service: TeacherService,
        tea_id: int,
        class_id: int,
        course_id: int,
        db: AsyncSession,
    ) -> tuple[dict, list[dict], list[dict]]:
        """Collect deterministic class data before handing the job to the AI worker."""
        summary = await teacher_service.get_class_summary(tea_id, class_id, course_id, db)
        difficult_knowledge = await teacher_service.get_difficult_knowledge_points(
            tea_id, class_id, course_id, db
        )
        difficult_chapters = await teacher_service.get_difficult_chapters(
            tea_id, class_id, course_id, db
        )
        return summary, difficult_knowledge, difficult_chapters

    async def reconcile(self, plan: LessonPlan, db: AsyncSession) -> LessonPlan:
        """Pull one active job's state from the AI worker and persist its final result."""
        if plan.status not in _ACTIVE_STATUSES:
            return plan
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/lesson-plans/tasks/{plan.task_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError:
            return plan

        status = result.get("status")
        if status not in _ALL_STATUSES:
            return plan
        plan.status = status
        if status == "completed":
            draft = result.get("draft")
            if isinstance(draft, dict):
                quality_report = result.get("quality_report")
                if isinstance(quality_report, dict):
                    draft = {**draft, "quality_report": quality_report}
                plan.content = draft
                plan.title = str(draft.get("title") or plan.title)[:256]
            plan.file_name = result.get("file_name") or plan.file_name
            plan.error_message = None
        elif status == "failed":
            plan.error_message = str(result.get("error") or "教案生成失败，请稍后重试。")[:4000]
        await db.commit()
        await db.refresh(plan)
        return plan

    async def list_for_teacher(self, tea_id: int, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(LessonPlan, Class.class_name, Course.course_name)
            .join(Class, Class.class_id == LessonPlan.class_id)
            .join(Course, Course.course_id == LessonPlan.course_id)
            .where(LessonPlan.tea_id == tea_id)
            .order_by(LessonPlan.created_at.desc())
            .limit(50)
        )
        rows = result.all()
        items: list[dict] = []
        for plan, class_name, course_name in rows:
            await self.reconcile(plan, db)
            items.append(self._serialize(plan, class_name=class_name, course_name=course_name))
        return items

    async def get_for_teacher(self, tea_id: int, lesson_plan_id: int, db: AsyncSession) -> dict:
        result = await db.execute(
            select(LessonPlan).where(
                LessonPlan.lesson_plan_id == lesson_plan_id,
                LessonPlan.tea_id == tea_id,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ValueError("教案不存在或无权访问")
        await self.reconcile(plan, db)
        class_name, course_name = await self._load_names(plan, db)
        return self._serialize(plan, class_name=class_name, course_name=course_name)

    async def download_for_teacher(
        self, tea_id: int, lesson_plan_id: int, db: AsyncSession
    ) -> tuple[bytes, str]:
        plan_data = await self.get_for_teacher(tea_id, lesson_plan_id, db)
        if plan_data["status"] != "completed":
            raise ValueError("教案尚未生成完成")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/lesson-plans/tasks/{plan_data['task_id']}/download",
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.content, plan_data["file_name"] or "lesson-plan.pptx"
        except httpx.HTTPError as exc:
            raise ValueError("PPTX 文件暂时不可下载，请稍后重试") from exc

    async def preview_html_for_teacher(
        self, tea_id: int, lesson_plan_id: int, db: AsyncSession
    ) -> bytes:
        content, _ = await self.preview_asset_for_teacher(tea_id, lesson_plan_id, "index.html", db)
        return content

    async def preview_asset_for_teacher(
        self, tea_id: int, lesson_plan_id: int, asset_path: str, db: AsyncSession
    ) -> tuple[bytes, str]:
        plan_data = await self.get_for_teacher(tea_id, lesson_plan_id, db)
        if plan_data["status"] != "completed":
            raise ValueError("教案尚未生成完成")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/lesson-plans/tasks/{plan_data['task_id']}/preview/{asset_path}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.content, response.headers.get("content-type", "application/octet-stream")
        except httpx.HTTPError as exc:
            raise ValueError("HTML 教案暂时不可预览，请稍后重试") from exc

    async def create_preview_ticket(self, tea_id: int, lesson_plan_id: int, db: AsyncSession) -> str:
        plan_data = await self.get_for_teacher(tea_id, lesson_plan_id, db)
        if plan_data["status"] != "completed":
            raise ValueError("教案尚未生成完成")
        token = secrets.token_urlsafe(32)
        redis = aioredis.from_url(settings.REDIS_URL)
        try:
            await redis.set(
                f"lesson-plan:preview:{token}",
                json.dumps({"teacher_id": tea_id, "lesson_plan_id": lesson_plan_id}),
                ex=_PREVIEW_TICKET_TTL,
            )
        finally:
            await redis.aclose()
        return token

    async def resolve_preview_ticket(self, token: str, lesson_plan_id: int) -> int | None:
        if not token or len(token) > 256:
            return None
        redis = aioredis.from_url(settings.REDIS_URL)
        try:
            raw = await redis.get(f"lesson-plan:preview:{token}")
        finally:
            await redis.aclose()
        if not raw:
            return None
        try:
            data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        except json.JSONDecodeError:
            return None
        if int(data.get("lesson_plan_id", -1)) != int(lesson_plan_id):
            return None
        return int(data.get("teacher_id", 0)) or None
