"""Structured teaching-slide planner backed by the existing RAG pipeline."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agent.context import AgentContext
from app.engines.llm.client import LLMClient
from app.engines.rag.pipeline import DetailLevel, RagPipeline
from app.schemas.lesson_plan import (
    LessonPlanBlock,
    LessonPlanDraft,
    LessonPlanSlide,
    LessonPlanSubmitRequest,
)

logger = logging.getLogger(__name__)

_LAYOUTS = {
    "title",
    "objectives",
    "review",
    "knowledge_map",
    "concept",
    "comparison",
    "example",
    "difficulty_focus",
    "activity",
    "summary",
}

_LAYOUT_ORDER = {
    "title": 10,
    "review": 20,
    "objectives": 30,
    "knowledge_map": 40,
    "concept": 50,
    "comparison": 60,
    "example": 70,
    "difficulty_focus": 80,
    "activity": 90,
    "summary": 100,
}
_REQUIRED_LAYOUTS = {
    "title",
    "objectives",
    "knowledge_map",
    "concept",
    "example",
    "activity",
    "summary",
}
_UNSUPPORTED_FIGURE_REF = re.compile(r"图\s*\d+(?:\.\d+)+")


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
            return fallback.model_dump()
        try:
            # A second pass acts as a teaching-quality review: it catches
            # outline-like pages and fills structured blocks before rendering.
            review_response = await self.llm.chat(
                self._review_messages(request, rag_context, draft),
                temperature=0.18,
                response_format={"type": "json_object"},
            )
            reviewed = self._parse_json(review_response.content or "")
            draft = self._normalise(reviewed, request, draft)
        except Exception as exc:
            logger.warning("Lesson-plan teaching review failed; keeping first draft: %s", exc)
        html_fragments: dict[str, str] = {}
        try:
            html_response = await self.llm.chat(
                self._html_messages(request, draft),
                temperature=0.22,
                response_format={"type": "json_object"},
            )
            html_fragments = self._parse_html_fragments(html_response.content or "")
        except Exception as exc:
            logger.info("Lesson-plan HTML composition failed; renderer fallback will be used: %s", exc)
        result = draft.model_dump()
        if html_fragments:
            result["_html_fragments"] = html_fragments
        return result

    async def _retrieve_context(self, request: LessonPlanSubmitRequest) -> str:
        """Use course/graph-scoped RAG; a missing vector service must not block PPT generation."""
        query = f"{request.course_name} {request.section.path or request.section.name} 教学重点 概念 例题"
        try:
            result = await RagPipeline().run(
                query=query,
                top_k=8,
                detail_level=DetailLevel.TEXT,
                course_id=request.course_id,
                kg_graph_ids=[request.kg_graph_id] if request.kg_graph_id else None,
            )
            return result[:12000]
        except Exception as exc:
            logger.info("Lesson-plan RAG unavailable: %s", exc)
            return ""

    def _messages(self, request: LessonPlanSubmitRequest, rag_context: str) -> list[dict[str, str]]:
        difficult_names = [str(item.get("name")) for item in request.difficult_knowledge[:8] if item.get("name")]
        return [
            {
                "role": "system",
                "content": """你是计算机科学课程教案设计 Agent。根据给定课程小节、可追溯教材资料和班级真实学情，产出简洁、可授课的中文 PPT 教案结构。

硬性规则：
1. 只输出一个 JSON 对象，禁止 markdown。
2. 只能使用给定小节、资料和班级数据；资料不足时使用保守表述，不能编造事实、比例、公式或题目。
3. 每页最多 5 个短要点，每个要点不超过 42 个汉字；不要把讲稿堆到页面上。
4. 仅使用 layout：title、objectives、review、knowledge_map、concept、comparison、example、difficulty_focus、activity、summary。
5. 每份教案必须包含 title、objectives、knowledge_map、concept、example、activity、summary；若要求回顾且有上一小节，才加入 review。
6. 每页提供一个 takeaway（一句话结论，48字以内）。knowledge_map 额外输出 diagram_center 和恰好 3 个简短 diagram_nodes，每个节点不超过 22 个汉字。
7. 每页必须优先输出 blocks，而不是只输出 bullets。blocks 类型包括：highlight、text、comparison、process、question、code、table。
8. concept 至少包含 1 个 highlight 和 1 个 text；comparison 必须包含左右两组可比较内容；example 和 activity 必须包含 process，步骤为 3—4 步；review 必须包含 question，给出课堂提问、选项或教师讲解要点。
9. 只有教材资料中确实出现代码、表格或公式时才生成 code/table；不要凭空编造代码、数据或公式。不要引用“图2.2”“片段1”等未随 PPT 提供的图、片段或内部检索编号。
10. difficulty_focus 只能引用班级薄弱点；无薄弱点数据时不要创建此页。
11. 输出字段：title、summary、review_inserted、slides。每个 slide 包含 layout、title、takeaway、bullets、blocks、presenter_notes、source_refs；knowledge_map 还包含 diagram_center、diagram_nodes。""",
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
                        "class_difficult_knowledge": request.difficult_knowledge[:8],
                        "class_difficult_chapters": request.difficult_chapters[:6],
                        "retrieved_material": rag_context or "没有检索到可用教材片段。",
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _review_messages(
        self,
        request: LessonPlanSubmitRequest,
        rag_context: str,
        draft: LessonPlanDraft,
    ) -> list[dict[str, str]]:
        """Ask the model to review the first draft as a classroom lesson, not as prose."""
        return [
            {
                "role": "system",
                "content": """你是课堂教案审查 Agent。请审查下面的 PPT 教案初稿，并输出一个完整 JSON 教案。

审查目标：
1. 每页只保留一个课堂主张，但不能退化成标题加三条空泛 bullet。
2. 把定义页扩展为“核心判断 + 支撑依据”；把对比内容写成左右两组；把例题和活动写成可执行步骤；把回顾页写成可提问的问题。
3. 对计算机科学主题，优先补充真实的边界、输入输出、适用条件、代价或常见误区；只能依据提供的教材片段、知识图谱和班级数据。
4. 保留必要页面和页数，不要引入外部事实，不要引用未提供的图片编号、片段编号或内部检索编号。
5. 输出完整字段：title、summary、review_inserted、slides；每页包含 layout、title、takeaway、bullets、blocks、presenter_notes、source_refs。""",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "course": request.course_name,
                        "section": request.section.model_dump(),
                        "class": request.class_name,
                        "class_summary": request.class_summary,
                        "retrieved_material": rag_context or "没有检索到可用教材片段。",
                        "draft": draft.model_dump(),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _html_messages(self, request: LessonPlanSubmitRequest, draft: LessonPlanDraft) -> list[dict[str, str]]:
        """Have the Agent compose concise, semantic HTML fragments for the browser deck."""
        compact_slides = []
        for index, slide in enumerate(draft.slides, start=1):
            compact_blocks = []
            for block in slide.blocks[:4]:
                compact = {"type": block.type}
                for field in (
                    "title",
                    "text",
                    "items",
                    "steps",
                    "question",
                    "options",
                    "left_title",
                    "left_items",
                    "right_title",
                    "right_items",
                    "language",
                    "code",
                    "columns",
                    "rows",
                    "caption",
                ):
                    value = getattr(block, field)
                    if value:
                        compact[field] = value
                compact_blocks.append(compact)
            compact_slides.append(
                {
                    "index": index,
                    "layout": slide.layout,
                    "title": slide.title,
                    "takeaway": slide.takeaway,
                    "bullets": slide.bullets,
                    "blocks": compact_blocks,
                }
            )
        return [
            {
                "role": "system",
                "content": """你是课堂课件 HTML 编排 Agent。根据结构化教案，为每页生成一个简洁的 HTML 片段。

规则：
1. 只输出 JSON：{\"slides\":[{\"index\":1,\"html\":\"...\"}]}。
2. html 只能使用语义标签：div、article、h2、h3、p、ul、ol、li、strong、small、pre、code、table、thead、tbody、tr、th、td、details、summary。
3. 不得输出 style、script、iframe、img、svg、a，不得使用外部 URL、事件属性或 JavaScript；页面样式由系统统一提供。可使用 ai-highlight、ai-points、ai-comparison、ai-process、ai-question、ai-code、ai-table 这些 class。
4. 每页 html 不超过 1200 个字符；优先呈现核心判断、对比、步骤、问题、代码或表格，不要重复标题和 takeaway。
5. 只能使用输入中的事实和文字，不得补造数据、图片编号、题目答案或教材内容。""",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "course": request.course_name,
                        "section": request.section.model_dump(),
                        "slides": compact_slides,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _parse_html_fragments(self, text: str) -> dict[str, str]:
        data = self._parse_json(text)
        raw_slides = data.get("slides")
        if not isinstance(raw_slides, list):
            return {}
        fragments: dict[str, str] = {}
        for position, raw in enumerate(raw_slides, start=1):
            if not isinstance(raw, dict) or not isinstance(raw.get("html"), str):
                continue
            index = str(raw.get("index") or position)
            fragments[index] = raw["html"]
        return fragments

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
            title = self._clean_text(raw.get("title"), 80)
            raw_bullets = raw.get("bullets", [])
            if not isinstance(raw_bullets, list):
                raw_bullets = []
            bullets = [self._clean_text(item, 42) for item in raw_bullets if self._clean_text(item, 42)][:5]
            if not title:
                continue
            refs = [source_prefix]
            if layout == "review" and request.previous_section:
                refs.append(f"上一小节：{request.previous_section.path or request.previous_section.name}")
            if layout == "difficulty_focus" and request.difficult_knowledge:
                refs.append("班级错题知识点聚合")
            raw_nodes = raw.get("diagram_nodes", [])
            if not isinstance(raw_nodes, list):
                raw_nodes = []
            diagram_nodes = [self._clean_text(item, 22) for item in raw_nodes if self._clean_text(item, 22)][:3]
            if layout == "knowledge_map" and not diagram_nodes:
                diagram_nodes = bullets[1:4]
            diagram_center = self._clean_text(raw.get("diagram_center"), 72)
            if layout == "knowledge_map" and not diagram_center:
                diagram_center = bullets[0] if bullets else title
            blocks = self._normalise_blocks(raw.get("blocks"), layout, bullets)
            slides.append(
                LessonPlanSlide(
                    layout=layout,
                    title=title,
                    takeaway=self._clean_text(raw.get("takeaway"), 48),
                    bullets=bullets,
                    blocks=blocks,
                    presenter_notes=self._clean_text(raw.get("presenter_notes"), 500),
                    source_refs=refs,
                    diagram_center=diagram_center,
                    diagram_nodes=diagram_nodes,
                )
            )
        layouts = {slide.layout for slide in slides}
        if len(slides) < 6 or not _REQUIRED_LAYOUTS.issubset(layouts):
            return fallback
        if request.include_review and request.previous_section and "review" not in layouts:
            review = next((slide for slide in fallback.slides if slide.layout == "review"), None)
            if review is not None:
                slides.append(review)
        if not request.include_review:
            slides = [slide for slide in slides if slide.layout != "review"]
        slides = self._fit_slide_count(self._order_slides(slides), request.slide_count, request)
        if len(slides) < len(_REQUIRED_LAYOUTS):
            return fallback
        return LessonPlanDraft(
            title=self._clean_text(candidate.get("title") or fallback.title, 256),
            summary=self._clean_text(candidate.get("summary") or fallback.summary, 500),
            review_inserted=any(slide.layout == "review" for slide in slides),
            slides=slides,
        )

    def _normalise_blocks(
        self,
        raw_blocks: Any,
        layout: str,
        bullets: list[str],
    ) -> list[LessonPlanBlock]:
        """Validate rich blocks while keeping old bullet-only model output compatible."""
        blocks: list[LessonPlanBlock] = []
        if isinstance(raw_blocks, list):
            for raw in raw_blocks[:6]:
                if not isinstance(raw, dict):
                    continue
                block_type = str(raw.get("type") or "text")
                if block_type not in {"highlight", "text", "comparison", "process", "question", "code", "table"}:
                    block_type = "text"
                blocks.append(
                    LessonPlanBlock(
                        type=block_type,
                        title=self._clean_text(raw.get("title"), 80),
                        text=self._clean_text(raw.get("text"), 500),
                        items=self._clean_list(raw.get("items"), 6, 120),
                        steps=self._clean_list(raw.get("steps"), 5, 120),
                        question=self._clean_text(raw.get("question"), 240),
                        options=self._clean_list(raw.get("options"), 4, 100),
                        teacher_answer=self._clean_text(raw.get("teacher_answer"), 300),
                        left_title=self._clean_text(raw.get("left_title"), 60),
                        left_items=self._clean_list(raw.get("left_items"), 5, 120),
                        right_title=self._clean_text(raw.get("right_title"), 60),
                        right_items=self._clean_list(raw.get("right_items"), 5, 120),
                        language=self._clean_text(raw.get("language"), 30),
                        code=self._clean_code(raw.get("code"), 1600),
                        columns=self._clean_list(raw.get("columns"), 6, 60),
                        rows=[
                            self._clean_list(row, 6, 80)
                            for row in (raw.get("rows") if isinstance(raw.get("rows"), list) else [])[:8]
                            if isinstance(row, list)
                        ],
                        caption=self._clean_text(raw.get("caption"), 160),
                    )
                )
        if blocks:
            return blocks
        return self._derive_blocks(layout, bullets)

    @classmethod
    def _derive_blocks(cls, layout: str, bullets: list[str]) -> list[LessonPlanBlock]:
        """Create a useful rich representation for older or fallback LLM responses."""
        if not bullets:
            return []
        if layout in {"example", "activity"}:
            return [LessonPlanBlock(type="process", steps=bullets[:4])]
        if layout == "comparison":
            midpoint = max(1, len(bullets) // 2)
            return [
                LessonPlanBlock(
                    type="comparison",
                    left_title="本节对象",
                    left_items=bullets[:midpoint],
                    right_title="对照与迁移",
                    right_items=bullets[midpoint:],
                )
            ]
        if layout == "concept":
            return [
                LessonPlanBlock(type="highlight", text=bullets[0]),
                LessonPlanBlock(type="text", items=bullets[1:4]),
            ]
        if layout == "review":
            return [
                LessonPlanBlock(
                    type="question",
                    question=bullets[0],
                    options=bullets[1:4],
                )
            ]
        return [LessonPlanBlock(type="text", items=bullets[:5])]

    @staticmethod
    def _clean_list(value: Any, max_items: int, item_limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        for item in value[:max_items]:
            text = str(item or "").replace("\r", " ").replace("\n", " ").strip()
            if text:
                cleaned.append(_UNSUPPORTED_FIGURE_REF.sub("示意图", text)[:item_limit])
        return cleaned

    @staticmethod
    def _clean_code(value: Any, limit: int) -> str:
        code = str(value or "").replace("\r", "").strip()
        code = _UNSUPPORTED_FIGURE_REF.sub("示意图", code)
        return code[:limit]

    @staticmethod
    def _clean_text(value: Any, limit: int) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        text = _UNSUPPORTED_FIGURE_REF.sub("示意图", text)
        return text[:limit]

    @staticmethod
    def _order_slides(slides: list[LessonPlanSlide]) -> list[LessonPlanSlide]:
        return [
            slide
            for _, slide in sorted(
                enumerate(slides),
                key=lambda pair: (_LAYOUT_ORDER.get(pair[1].layout, 100), pair[0]),
            )
        ]

    @classmethod
    def _fit_slide_count(
        cls,
        slides: list[LessonPlanSlide],
        slide_count: int,
        request: LessonPlanSubmitRequest,
    ) -> list[LessonPlanSlide]:
        required = set(_REQUIRED_LAYOUTS)
        if request.include_review and request.previous_section:
            required.add("review")

        selected: list[LessonPlanSlide] = []
        selected_layouts: set[str] = set()
        for slide in slides:
            if slide.layout in required and slide.layout not in selected_layouts:
                selected.append(slide)
                selected_layouts.add(slide.layout)
        for slide in slides:
            if len(selected) >= slide_count:
                break
            if slide not in selected:
                selected.append(slide)
        return cls._order_slides(selected[:slide_count])

    def _fallback_draft(self, request: LessonPlanSubmitRequest, rag_context: str) -> LessonPlanDraft:
        section = request.section
        section_ref = f"知识图谱：{section.path or section.name}"
        difficult_names = [str(item.get("name")) for item in request.difficult_knowledge[:3] if item.get("name")]
        material_hint = "结合教材资料辨析核心定义与适用条件" if rag_context else "结合教师讲解辨析核心定义与适用条件"
        title_slide = LessonPlanSlide(
            layout="title",
            title=section.name,
            bullets=[request.course_name, request.class_name],
            source_refs=[section_ref],
        )
        objectives_slide = LessonPlanSlide(
            layout="objectives",
            title="学习目标",
            takeaway=f"本节结束时，学生能够解释“{section.name}”的核心关系。",
            bullets=[f"说清“{section.name}”的核心概念", "识别知识点之间的关联", "能用一个实例解释关键过程"],
            blocks=[
                LessonPlanBlock(type="text", items=[f"说清“{section.name}”的核心概念"]),
                LessonPlanBlock(type="text", items=["识别知识点之间的关联"]),
                LessonPlanBlock(type="text", items=["能用一个实例解释关键过程"]),
            ],
            source_refs=[section_ref],
        )
        previous_name = request.previous_section.name if request.previous_section else "课程前置知识"
        knowledge_map_slide = LessonPlanSlide(
            layout="knowledge_map",
            title="知识图谱定位",
            takeaway="先定位前置知识，再明确本节概念如何迁移到后续练习。",
            bullets=[section.name],
            source_refs=[section_ref],
            diagram_center=section.name,
            diagram_nodes=[f"前置：{previous_name}", "本节：核心概念", "后续：题目练习"],
        )
        concept_slide = LessonPlanSlide(
            layout="concept",
            title="核心概念与规则",
            takeaway="抓住定义、条件和结果三者之间的关系。",
            bullets=[material_hint, "用关键词区分相近概念", "先解释条件，再说明结论"],
            blocks=[
                LessonPlanBlock(type="highlight", text=material_hint),
                LessonPlanBlock(type="text", items=["用关键词区分相近概念", "先解释条件，再说明结论"]),
            ],
            source_refs=[section_ref, "教材 RAG 检索"],
        )
        comparison_slide = LessonPlanSlide(
            layout="comparison",
            title="把概念放进边界与取舍中理解",
            takeaway="不要只记名称，要同时说明适用条件和代价。",
            bullets=[
                f"本节对象：{section.name}",
                "关注定义、边界与适用条件",
                "迁移应用：回到题目场景",
                "关注判断依据与可能代价",
            ],
            blocks=[
                LessonPlanBlock(
                    type="comparison",
                    left_title="本节对象",
                    left_items=[f"{section.name}", "定义与边界", "适用条件"],
                    right_title="迁移应用",
                    right_items=["题目场景", "判断依据", "可能代价"],
                )
            ],
            source_refs=[section_ref],
        )
        example_slide = LessonPlanSlide(
            layout="example",
            title="例题与过程演示",
            takeaway="通过一个具体过程，把抽象关系转成可检查的步骤。",
            bullets=["明确输入与问题", "逐步跟踪状态变化", "核对结果并解释依据", "改变一个条件进行迁移"],
            blocks=[LessonPlanBlock(type="process", steps=["明确输入与问题", "逐步跟踪状态变化", "核对结果并解释依据", "改变一个条件进行迁移"])],
            source_refs=[section_ref],
        )
        activity_slide = LessonPlanSlide(
            layout="activity",
            title="课堂练习与反馈",
            takeaway="让学生先做出判断，再用自己的语言说明理由。",
            bullets=["独立完成判断", "同伴互相说明理由", "教师收集典型错误", "用变式题检查迁移"],
            blocks=[LessonPlanBlock(type="process", steps=["独立完成判断", "同伴互相说明理由", "教师收集典型错误", "用变式题检查迁移"])],
            source_refs=[section_ref],
        )
        summary_slide = LessonPlanSlide(
            layout="summary",
            title="本节小结与课后任务",
            takeaway="用一句话复述本节核心关系，并把它连接到下一步练习。",
            bullets=[f"回顾“{section.name}”的关键术语", "完成对应知识点的针对性练习", "记录仍不确定的一个问题"],
            blocks=[
                LessonPlanBlock(type="text", items=[f"回顾“{section.name}”的关键术语"]),
                LessonPlanBlock(type="text", items=["完成对应知识点的针对性练习"]),
                LessonPlanBlock(type="question", question="还有哪一个问题需要在练习中验证？"),
            ],
            source_refs=[section_ref],
        )
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
                takeaway="用上一节的关键概念，为本节新知识建立入口。",
                bullets=[mastery_text, "用一道口头问题唤回前置概念", "连接本节的新旧知识"],
                blocks=[
                    LessonPlanBlock(
                        type="question",
                        question="上一节最关键的概念是什么？它解决了什么问题？",
                        options=["先独立回忆", "和同伴互相补充", "连接本节的新知识"],
                        teacher_answer=mastery_text,
                    )
                ],
                source_refs=[section_ref, f"上一小节：{request.previous_section.path or request.previous_section.name}", "班级学情汇总"],
            )
            slides.append(review_slide)
        slides.extend(
            [
                knowledge_map_slide,
                concept_slide,
                comparison_slide,
                example_slide,
            ]
        )
        difficulty_slide = None
        if difficult_names:
            difficulty_slide = LessonPlanSlide(
                layout="difficulty_focus",
                title="班级易错点",
                takeaway="把班级高频错误转成课堂中的重点检查点。",
                bullets=[f"重点辨析：{name}" for name in difficult_names],
                blocks=[LessonPlanBlock(type="text", items=[f"重点辨析：{name}" for name in difficult_names])],
                source_refs=["班级错题知识点聚合", section_ref],
            )
            slides.append(difficulty_slide)
        slides.extend([activity_slide, summary_slide])
        while len(slides) < request.slide_count:
            slides.insert(
                -2,
                LessonPlanSlide(
                    layout="concept",
                    title="要点巩固",
                    takeaway="回到定义、条件与例子，完成一次快速自检。",
                    bullets=["回到定义、条件与例子进行核对", "用自己的语言复述关键过程"],
                    blocks=[LessonPlanBlock(type="text", items=["回到定义、条件与例子进行核对", "用自己的语言复述关键过程"])],
                    source_refs=[section_ref],
                ),
            )
        slides = self._fit_slide_count(self._order_slides(slides), request.slide_count, request)
        return LessonPlanDraft(
            title=f"{section.name} 教案",
            summary=f"面向{request.class_name}的{request.course_name}《{section.name}》课堂教案。",
            review_inserted=any(slide.layout == "review" for slide in slides),
            slides=slides,
        )


async def execute_lesson_plan(context: AgentContext, llm: LLMClient, payload: dict[str, Any]) -> dict[str, Any]:
    """Agent Runtime workflow entry point."""
    return await LessonPlanAgent(llm).generate(context, payload)
