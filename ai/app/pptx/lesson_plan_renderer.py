"""Deterministic, editable PPTX renderer for a validated lesson-plan draft."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.schemas.lesson_plan import LessonPlanDraft


def _safe_stem(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip(" ._")
    return value[:80] or "lesson-plan"


def render_lesson_plan(
    draft: dict[str, Any],
    output_dir: Path,
    task_id: str,
    course_name: str,
    class_name: str,
) -> tuple[Path, str]:
    """Render a native, editable PPTX. Imports stay lazy so other AI tasks keep working if the optional dependency is absent."""
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt
    except ImportError as exc:  # pragma: no cover - depends on deployment extras
        raise RuntimeError("缺少 python-pptx，请在 AI 服务环境中安装 requirements.txt") from exc

    spec = LessonPlanDraft.model_validate(draft)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_stem(spec.title)}_{task_id[:8]}.pptx"
    output_path = output_dir / filename

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    navy = RGBColor(23, 58, 110)
    blue = RGBColor(45, 90, 192)
    teal = RGBColor(14, 116, 144)
    ink = RGBColor(30, 41, 59)
    muted = RGBColor(71, 85, 105)
    canvas = RGBColor(248, 250, 252)
    border = RGBColor(226, 232, 240)
    white = RGBColor(255, 255, 255)

    def add_text(slide, text: str, x: float, y: float, w: float, h: float, size: int, color, bold: bool = False, align=None):
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = shape.text_frame
        tf.clear()
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0)
        tf.margin_top = tf.margin_bottom = Inches(0)
        paragraph = tf.paragraphs[0]
        paragraph.text = text
        paragraph.font.name = "Microsoft YaHei"
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = color
        if align is not None:
            paragraph.alignment = align
        return shape

    def add_background(slide):
        background = slide.background.fill
        background.solid()
        background.fore_color.rgb = canvas
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.17), Inches(7.5))
        bar.fill.solid()
        bar.fill.fore_color.rgb = blue
        bar.line.fill.background()

    def add_footer(slide, index: int, refs: list[str]):
        ref_text = " · ".join(refs[:2]) if refs else f"{course_name} · {class_name}"
        add_text(slide, ref_text[:110], 0.65, 7.05, 10.7, 0.18, 8, muted)
        add_text(slide, f"{index:02d}", 12.05, 6.94, 0.55, 0.24, 10, blue, bold=True, align=PP_ALIGN.RIGHT)

    def add_title(slide, title: str, eyebrow: str):
        add_text(slide, eyebrow.upper(), 0.65, 0.45, 5.3, 0.22, 10, blue, bold=True)
        add_text(slide, title, 0.65, 0.76, 11.8, 0.55, 30, navy, bold=True)
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(1.42), Inches(1.2), Inches(0.05))
        line.fill.solid()
        line.fill.fore_color.rgb = teal
        line.line.fill.background()

    for index, item in enumerate(spec.slides, start=1):
        slide = prs.slides.add_slide(blank)
        add_background(slide)
        if item.layout == "title":
            accent = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.72), Inches(0.65), Inches(11.7), Inches(5.85))
            accent.fill.solid()
            accent.fill.fore_color.rgb = navy
            accent.line.fill.background()
            add_text(slide, course_name.upper(), 1.25, 1.35, 7.0, 0.25, 13, RGBColor(191, 219, 254), bold=True)
            add_text(slide, item.title, 1.25, 2.1, 9.8, 1.25, 38, white, bold=True)
            subtitle = " · ".join(item.bullets[:2]) or class_name
            add_text(slide, subtitle, 1.25, 3.72, 8.7, 0.4, 19, RGBColor(226, 232, 240))
            add_text(slide, "智教慧学 · AI 教案", 1.25, 5.72, 4.0, 0.28, 12, RGBColor(191, 219, 254))
        else:
            add_title(slide, item.title, item.layout.replace("_", " "))
            if item.layout == "knowledge_map":
                # Draw connectors before the nodes so the hierarchy stays visible
                # without preventing teachers from editing any individual node.
                for x, y, w, h in (
                    (3.55, 2.48, 0.96, 0.07),
                    (8.52, 2.48, 0.96, 0.07),
                    (6.47, 3.55, 0.07, 1.04),
                ):
                    connector = slide.shapes.add_shape(
                        MSO_SHAPE.RECTANGLE,
                        Inches(x),
                        Inches(y),
                        Inches(w),
                        Inches(h),
                    )
                    connector.fill.solid()
                    connector.fill.fore_color.rgb = RGBColor(147, 197, 253)
                    connector.line.fill.background()
                center = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.45), Inches(2.5), Inches(4.1), Inches(1.1))
                center.fill.solid()
                center.fill.fore_color.rgb = blue
                center.line.fill.background()
                add_text(slide, item.bullets[0] if item.bullets else item.title, 4.72, 2.83, 3.56, 0.44, 20, white, bold=True, align=PP_ALIGN.CENTER)
                supplied_labels = item.bullets[1:4]
                labels = [
                    supplied_labels[0] if len(supplied_labels) > 0 else "前置知识",
                    supplied_labels[1] if len(supplied_labels) > 1 else "后续应用",
                    supplied_labels[2] if len(supplied_labels) > 2 else "学习迁移",
                ]
                positions = [(0.95, 2.15), (9.45, 2.15), (5.2, 4.55)]
                for label, (x, y) in zip(labels, positions):
                    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(2.65), Inches(0.72))
                    box.fill.solid()
                    box.fill.fore_color.rgb = white
                    box.line.color.rgb = border
                    add_text(slide, label, x + 0.18, y + 0.22, 2.29, 0.24, 15, ink, bold=True, align=PP_ALIGN.CENTER)
            else:
                x = 0.82
                y = 1.75
                for bullet in item.bullets[:5]:
                    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y + 0.08), Inches(0.12), Inches(0.12))
                    dot.fill.solid()
                    dot.fill.fore_color.rgb = teal if item.layout in {"activity", "example"} else blue
                    dot.line.fill.background()
                    add_text(slide, bullet, x + 0.28, y, 10.85, 0.48, 20, ink)
                    y += 0.83
                if item.presenter_notes:
                    note = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.85), Inches(5.45), Inches(3.2), Inches(0.8))
                    note.fill.solid()
                    note.fill.fore_color.rgb = white
                    note.line.color.rgb = border
                    add_text(slide, item.presenter_notes[:70], 9.08, 5.67, 2.75, 0.32, 11, muted)
        add_footer(slide, index, item.source_refs)

    prs.save(output_path)
    return output_path, filename
