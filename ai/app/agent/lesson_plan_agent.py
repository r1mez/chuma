"""Structured teaching-slide planner backed by the existing RAG pipeline."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.context import AgentContext
from app.engines.llm.client import LLMClient
from app.engines.rag.pipeline import DetailLevel, RagPipeline
from app.schemas.lesson_plan import LessonPlanDraft, LessonPlanSlide, LessonPlanSubmitRequest

logger = logging.getLogger(__name__)

_LAYOUTS = {
    "title",
    "objectives",
    "review",
    "knowledge_map",
    "concept",
    "example",
    "difficulty_focus",
    "activity",
    "summary",
}


class LessonPlanAgent:
    """Generate a source-aware, renderer-safe lesson-plan specification."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate(self, context: AgentContext, payload: dict[str, Any]) -> dict[str, Any]:
        request = LessonPlanSubmitRequest.model_validate(payload)
        rag_context = await self._retrieve_context(request)
        fallback = self._fallback_draft(request, rag_context)
        try:
            response = await self.llm.chat(
                self._messages(request, rag_context),
                temperature=0.35,
                response_format={"type": "json_object"},
            )
            candidate = self._parse_json(response.content or "")
            draft = self._normalise(candidate, request, fallback)
        except Exception as exc:
            logger.warning("Lesson-plan LLM generation failed; using deterministic draft: %s", exc)
            draft = fallback
        return draft.model_dump()

    async def _retrieve_context(self, request: LessonPlanSubmitRequest) -> str:
        """Use course/graph-scoped RAG; a missing vector service must not block PPT generation."""
        query = f"{request.course_name} {request.section.path or request.section.name} 教学重点 概念 例题"
        try:
            result = await RagPipeline().run(
                query=query,
                top_k=4,
                detail_level=DetailLevel.ENTITIES,
                course_id=request.course_id,
                kg_graph_ids=[request.kg_graph_id] if request.kg_graph_id else None,
            )
            return result[:7000]
        except Exception as exc:
            logger.info("Lesson-plan RAG unavailable: %s", exc)
            return ""

    def _messages(self, request: LessonPlanSubmitRequest, rag_context: str) -> list[dict[str, str]]:
        difficult_names = [str(item.get("name")) for item in request.difficult_knowledge[:5] if item.get("name")]
        return [
            {
                "role": "system",
                "content": """你是计算机科学课程教案设计 Agent。根据给定课程小节、可追溯教材资料和班级真实学情，产出简洁、可授课的中文 PPT 教案结构。

硬性规则：
1. 只输出一个 JSON 对象，禁止 markdown。
2. 只能使用给定小节、资料和班级数据；资料不足时使用保守表述，不能编造事实、比例、公式或题目。
3. 每页最多 5 个短要点，每个要点不超过 34 个汉字；不要把讲稿堆到页面上。
4. 仅使用 layout：title、objectives、review、knowledge_map、concept、example、difficulty_focus、activity、summary。
5. 每份教案必须包含 title、objectives、knowledge_map、concept、example、activity、summary；若要求回顾且有上一小节，才加入 review。
6. difficulty_focus 只能引用班级薄弱点；无薄弱点数据时不要创建此页。
7. 输出字段：title、summary、review_inserted、slides。每个 slide 包含 layout、title、bullets、presenter_notes、source_refs。""",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "course": request.course_name,
                        "class": request.class_name,
                        "target_section": request.section.model_dump(),
                        "previous_section": request.previous_section.model_dump() if request.previous_section else None,
                        "include_review": request.include_review,
                        "requested_slide_count": request.slide_count,
                        "class_summary": request.class_summary,
                        "class_difficult_knowledge": difficult_names,
                        "class_difficult_chapters": request.difficult_chapters[:4],
                        "retrieved_material": rag_context or "没有检索到可用教材片段。",
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].removeprefix("json").strip() if len(parts) > 1 else text
        first, last = text.find("{"), text.rfind("}")
        if first < 0 or last <= first:
            raise ValueError("LLM did not return a JSON object")
        data = json.loads(text[first:last + 1])
        if not isinstance(data, dict):
            raise ValueError("LLM output is not an object")
        return data

    def _normalise(
        self,
        candidate: dict[str, Any],
        request: LessonPlanSubmitRequest,
        fallback: LessonPlanDraft,
    ) -> LessonPlanDraft:
        raw_slides = candidate.get("slides")
        if not isinstance(raw_slides, list):
            return fallback
        source_prefix = f"知识图谱：{request.section.path or request.section.name}"
        slides: list[LessonPlanSlide] = []
        for raw in raw_slides:
            if not isinstance(raw, dict):
                continue
            layout = str(raw.get("layout") or "concept")
            if layout not in _LAYOUTS:
                layout = "concept"
            title = str(raw.get("title") or "").strip()[:80]
            bullets = [str(item).strip()[:60] for item in raw.get("bullets", []) if str(item).strip()][:5]
            if not title:
                continue
            refs = [source_prefix]
            if layout == "review" and request.previous_section:
                refs.append(f"上一小节：{request.previous_section.path or request.previous_section.name}")
            if layout == "difficulty_focus" and request.difficult_knowledge:
                refs.append("班级错题知识点聚合")
            slides.append(
                LessonPlanSlide(
                    layout=layout,
                    title=title,
                    bullets=bullets,
                    presenter_notes=str(raw.get("presenter_notes") or "")[:500],
                    source_refs=refs,
                )
            )
        required = {"title", "objectives", "knowledge_map", "concept", "example", "activity", "summary"}
        if len(slides) < 6 or not required.issubset({slide.layout for slide in slides}):
            return fallback
        slides = slides[:request.slide_count]
        if len(slides) < 6:
            return fallback
        return LessonPlanDraft(
            title=str(candidate.get("title") or fallback.title)[:256],
            summary=str(candidate.get("summary") or fallback.summary)[:500],
            review_inserted=any(slide.layout == "review" for slide in slides),
            slides=slides,
        )

    def _fallback_draft(self, request: LessonPlanSubmitRequest, rag_context: str) -> LessonPlanDraft:
        section = request.section
        section_ref = f"知识图谱：{section.path or section.name}"
        difficult_names = [str(item.get("name")) for item in request.difficult_knowledge[:3] if item.get("name")]
        material_hint = "结合教材资料辨析核心定义与适用条件" if rag_context else "结合教师讲解辨析核心定义与适用条件"
        title_slide = LessonPlanSlide(layout="title", title=section.name, bullets=[request.course_name, request.class_name], source_refs=[section_ref])
        objectives_slide = LessonPlanSlide(
            layout="objectives",
            title="学习目标",
            bullets=[f"说清“{section.name}”的核心概念", "识别知识点之间的关联", "能用一个实例解释关键过程"],
            source_refs=[section_ref],
        )
        knowledge_map_slide = LessonPlanSlide(layout="knowledge_map", title="知识图谱定位", bullets=[section.path or section.name, "明确本节的前置与后续学习位置"], source_refs=[section_ref])
        concept_slide = LessonPlanSlide(layout="concept", title="核心概念与规则", bullets=[material_hint, "用关键词区分相近概念", "先解释条件，再说明结论"], source_refs=[section_ref, "教材 RAG 检索"])
        example_slide = LessonPlanSlide(layout="example", title="例题与过程演示", bullets=["从输入、状态变化到输出逐步推演", "引导学生说明每一步的依据", "保留一个可变条件供课堂追问"], source_refs=[section_ref])
        activity_slide = LessonPlanSlide(layout="activity", title="课堂练习与反馈", bullets=["先独立判断，再同伴说明理由", "教师收集典型错误并即时纠偏", "用一个变式题检查迁移"], source_refs=[section_ref])
        summary_slide = LessonPlanSlide(layout="summary", title="本节小结与课后任务", bullets=[f"回顾“{section.name}”的关键术语", "完成对应知识点的针对性练习", "记录仍不确定的一个问题"], source_refs=[section_ref])
        slides = [
            title_slide,
            objectives_slide,
        ]
        review_slide = None
        if request.include_review and request.previous_section:
            mastery = request.class_summary.get("average_mastery")
            mastery_text = f"班级平均掌握度：{mastery}%" if mastery is not None else "依据上一节学习记录进行快速诊断"
            review_slide = LessonPlanSlide(
                layout="review",
                title=f"回顾：{request.previous_section.name}",
                bullets=[mastery_text, "用一道口头问题唤回前置概念", "连接本节的新旧知识"],
                source_refs=[section_ref, f"上一小节：{request.previous_section.path or request.previous_section.name}", "班级学情汇总"],
            )
            slides.append(review_slide)
        slides.extend(
            [
                knowledge_map_slide,
                concept_slide,
                example_slide,
            ]
        )
        difficulty_slide = None
        if difficult_names:
            difficulty_slide = LessonPlanSlide(
                layout="difficulty_focus", title="班级易错点", bullets=[f"重点辨析：{name}" for name in difficult_names], source_refs=["班级错题知识点聚合", section_ref]
            )
            slides.append(difficulty_slide)
        slides.extend([activity_slide, summary_slide])
        while len(slides) < request.slide_count:
            slides.insert(
                -2,
                LessonPlanSlide(
                    layout="concept",
                    title="要点巩固",
                    bullets=["回到定义、条件与例子进行核对", "用自己的语言复述关键过程"],
                    source_refs=[section_ref],
                ),
            )
        if len(slides) > request.slide_count and difficulty_slide is not None:
            slides.remove(difficulty_slide)
        if len(slides) > request.slide_count and review_slide is not None:
            slides.remove(review_slide)
        return LessonPlanDraft(
            title=f"{section.name} 教案",
            summary=f"面向{request.class_name}的{request.course_name}《{section.name}》课堂教案。",
            review_inserted=any(slide.layout == "review" for slide in slides),
            slides=slides[:request.slide_count],
        )


async def execute_lesson_plan(context: AgentContext, llm: LLMClient, payload: dict[str, Any]) -> dict[str, Any]:
    """Agent Runtime workflow entry point."""
    return await LessonPlanAgent(llm).generate(context, payload)
