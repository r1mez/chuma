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

    def add_text(
        slide,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        size: int,
        color,
        bold: bool = False,
        align=None,
        font_name: str = "Microsoft YaHei",
    ):
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = shape.text_frame
        tf.clear()
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0)
        tf.margin_top = tf.margin_bottom = Inches(0)
        paragraph = tf.paragraphs[0]
        paragraph.text = text
        paragraph.font.name = font_name
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
        graph_ref = next((ref for ref in refs if ref.startswith("知识图谱：")), "")
        if graph_ref:
            path_parts = [part.strip() for part in graph_ref.removeprefix("知识图谱：").split("/") if part.strip()]
            ref_text = "知识图谱 · " + " / ".join(path_parts[-2:])
        else:
            ref_text = refs[0] if refs else f"{course_name} · {class_name}"
        add_text(slide, ref_text[:92], 0.65, 7.05, 10.7, 0.18, 9, muted)
        add_text(slide, f"{index:02d}", 12.05, 6.94, 0.55, 0.24, 10, blue, bold=True, align=PP_ALIGN.RIGHT)

    def add_takeaway(slide, text: str) -> float:
        if not text:
            return 1.75
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.82), Inches(1.72), Inches(0.05), Inches(0.38))
        accent.fill.solid()
        accent.fill.fore_color.rgb = teal
        accent.line.fill.background()
        add_text(slide, text[:80], 1.03, 1.70, 11.0, 0.42, 16, muted)
        return 2.25

    def add_bullets(slide, item, start_y: float) -> None:
        y = start_y
        for bullet in item.bullets[:5]:
            line_count = 2 if len(bullet) > 26 else 1
            text_height = 0.68 if line_count == 2 else 0.42
            dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.82), Inches(y + 0.09), Inches(0.12), Inches(0.12))
            dot.fill.solid()
            dot.fill.fore_color.rgb = teal if item.layout in {"activity", "example"} else blue
            dot.line.fill.background()
            add_text(slide, bullet, 1.10, y, 10.8, text_height, 20, ink)
            y += 0.86 if line_count == 2 else 0.76

    def _card_texts(item) -> list[str]:
        texts: list[str] = []
        for block in item.blocks:
            if block.type == "text":
                texts.extend(block.items or ([block.text] if block.text else []))
            elif block.type == "highlight" and block.text:
                texts.append(block.text)
        return texts[:5] or item.bullets[:5]

    def _block_of_type(item, block_type: str):
        return next((block for block in item.blocks if block.type == block_type), None)

    def add_process(slide, item, start_y: float) -> None:
        process = _block_of_type(item, "process")
        steps = (process.steps if process else item.bullets)[:4]
        if not steps:
            return
        gap = 0.18
        left = 0.82
        total_width = 11.7
        box_width = (total_width - gap * (len(steps) - 1)) / len(steps)
        box_y = start_y + 0.22
        box_height = 1.55

        for index in range(len(steps) - 1):
            connector_x = left + (index + 1) * box_width + index * gap
            connector = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(connector_x),
                Inches(box_y + 0.72),
                Inches(gap),
                Inches(0.05),
            )
            connector.fill.solid()
            connector.fill.fore_color.rgb = RGBColor(147, 197, 253)
            connector.line.fill.background()

        for index, step in enumerate(steps, start=1):
            x = left + (index - 1) * (box_width + gap)
            box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(box_y), Inches(box_width), Inches(box_height))
            box.fill.solid()
            box.fill.fore_color.rgb = white
            box.line.color.rgb = border
            badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.18), Inches(box_y + 0.18), Inches(0.38), Inches(0.38))
            badge.fill.solid()
            badge.fill.fore_color.rgb = teal
            badge.line.fill.background()
            add_text(slide, str(index), x + 0.18, box_y + 0.26, 0.38, 0.16, 10, white, bold=True, align=PP_ALIGN.CENTER)
            add_text(slide, step, x + 0.18, box_y + 0.72, box_width - 0.36, 0.62, 16, ink, bold=True, align=PP_ALIGN.CENTER)

    def add_cards(slide, bullets: list[str], start_y: float, accent_color, card_height: float = 1.55) -> None:
        """Render independent classroom points as editable cards, not a repeated bullet list."""
        cards = bullets[:4]
        if not cards:
            return
        gap = 0.18
        left = 0.82
        total_width = 11.7
        card_width = (total_width - gap * (len(cards) - 1)) / len(cards)
        card_y = start_y + 0.28
        for index, text in enumerate(cards, start=1):
            x = left + (index - 1) * (card_width + gap)
            box = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(x),
                Inches(card_y),
                Inches(card_width),
                Inches(card_height),
            )
            box.fill.solid()
            box.fill.fore_color.rgb = white
            box.line.color.rgb = border
            stripe = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(x),
                Inches(card_y),
                Inches(card_width),
                Inches(0.08),
            )
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = accent_color
            stripe.line.fill.background()
            badge = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(x + 0.18),
                Inches(card_y + 0.22),
                Inches(0.36),
                Inches(0.36),
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = accent_color
            badge.line.fill.background()
            add_text(slide, str(index), x + 0.18, card_y + 0.30, 0.36, 0.14, 9, white, bold=True, align=PP_ALIGN.CENTER)
            text_size = 15 if len(text) > 30 else 16
            add_text(slide, text, x + 0.18, card_y + 0.76, card_width - 0.36, card_height - 0.94, text_size, ink, bold=True, align=PP_ALIGN.CENTER)

    def add_concept(slide, item, start_y: float) -> None:
        """Give a concept slide a memorable anchor plus supporting evidence cards."""
        highlight = _block_of_type(item, "highlight")
        headline = highlight.text if highlight and highlight.text else (item.bullets[0] if item.bullets else "")
        supporting = _card_texts(item)
        if headline and supporting and supporting[0] == headline:
            supporting = supporting[1:]
        if not headline:
            add_bullets(slide, item, start_y)
            return
        callout_y = start_y + 0.24
        callout = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.82),
            Inches(callout_y),
            Inches(11.7),
            Inches(1.16),
        )
        callout.fill.solid()
        callout.fill.fore_color.rgb = RGBColor(239, 246, 255)
        callout.line.color.rgb = RGBColor(191, 219, 254)
        add_text(slide, "核心判断", 1.08, callout_y + 0.18, 1.1, 0.2, 10, blue, bold=True)
        headline_size = 21 if len(headline) > 26 else 24
        add_text(slide, headline, 1.08, callout_y + 0.49, 11.15, 0.48, headline_size, navy, bold=True)
        if supporting:
            add_cards(slide, supporting, start_y + 1.30, teal, card_height=1.42)

    def add_comparison(slide, item, start_y: float) -> None:
        block = _block_of_type(item, "comparison")
        if block is None:
            midpoint = max(1, len(item.bullets) // 2)
            left_title, left_items = "本节对象", item.bullets[:midpoint]
            right_title, right_items = "对照与迁移", item.bullets[midpoint:]
        else:
            left_title, left_items = block.left_title or "本节对象", block.left_items
            right_title, right_items = block.right_title or "对照与迁移", block.right_items
        y = start_y + 0.24
        for x, title, items, accent in (
            (0.82, left_title, left_items, blue),
            (6.98, right_title, right_items, teal),
        ):
            panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(5.54), Inches(2.55))
            panel.fill.solid()
            panel.fill.fore_color.rgb = white
            panel.line.color.rgb = border
            stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(5.54), Inches(0.10))
            stripe.fill.solid()
            stripe.fill.fore_color.rgb = accent
            stripe.line.fill.background()
            add_text(slide, title, x + 0.28, y + 0.30, 4.95, 0.35, 24, navy, bold=True)
            item_y = y + 0.92
            for index, value in enumerate(items[:4], start=1):
                add_text(slide, f"{index:02d}", x + 0.28, item_y, 0.38, 0.22, 11, accent, bold=True)
                add_text(slide, value, x + 0.82, item_y - 0.02, 4.35, 0.42, 16, ink)
                item_y += 0.43

    def add_question(slide, item, start_y: float) -> None:
        block = _block_of_type(item, "question")
        question = block.question if block else (item.bullets[0] if item.bullets else "请结合本节知识说明你的判断。")
        options = block.options if block else item.bullets[1:4]
        y = start_y + 0.24
        prompt = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(y), Inches(11.7), Inches(1.20))
        prompt.fill.solid()
        prompt.fill.fore_color.rgb = RGBColor(240, 253, 250)
        prompt.line.color.rgb = RGBColor(153, 246, 228)
        add_text(slide, "课堂问题", 1.10, y + 0.18, 1.1, 0.22, 11, teal, bold=True)
        add_text(slide, question, 1.10, y + 0.52, 11.0, 0.43, 24 if len(question) < 28 else 21, navy, bold=True)
        if options:
            gap = 0.18
            width = (11.7 - gap * (len(options[:4]) - 1)) / len(options[:4])
            for index, option in enumerate(options[:4], start=1):
                x = 0.82 + (index - 1) * (width + gap)
                box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y + 1.58), Inches(width), Inches(1.05))
                box.fill.solid()
                box.fill.fore_color.rgb = white
                box.line.color.rgb = border
                add_text(slide, str(index), x + 0.18, y + 1.82, 0.30, 0.20, 12, teal, bold=True)
                add_text(slide, option, x + 0.60, y + 1.78, width - 0.78, 0.42, 16, ink, bold=True)

    def add_code(slide, block, start_y: float) -> None:
        code = block.code.strip()
        if not code:
            return
        y = start_y + 0.22
        panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.82), Inches(y), Inches(11.7), Inches(2.65))
        panel.fill.solid()
        panel.fill.fore_color.rgb = RGBColor(15, 23, 42)
        panel.line.fill.background()
        add_text(slide, block.language.upper() or "CODE", 1.10, y + 0.22, 2.0, 0.22, 10, RGBColor(125, 211, 252), bold=True)
        add_text(slide, code, 1.10, y + 0.62, 11.0, 1.72, 16, RGBColor(226, 232, 240), font_name="Consolas")
        if block.caption:
            add_text(slide, block.caption, 1.10, y + 2.28, 11.0, 0.22, 12, RGBColor(148, 163, 184))

    def add_table(slide, block, start_y: float) -> None:
        if not block.columns or not block.rows:
            return
        row_count = min(len(block.rows), 7) + 1
        col_count = min(len(block.columns), 6)
        table_shape = slide.shapes.add_table(row_count, col_count, Inches(0.82), Inches(start_y + 0.24), Inches(11.7), Inches(2.75))
        table = table_shape.table
        for column_index, column in enumerate(block.columns[:col_count]):
            cell = table.cell(0, column_index)
            cell.text = column
            cell.fill.solid()
            cell.fill.fore_color.rgb = blue
        for row_index, row in enumerate(block.rows[: row_count - 1], start=1):
            for column_index, value in enumerate(row[:col_count]):
                cell = table.cell(row_index, column_index)
                cell.text = value
                cell.fill.solid()
                cell.fill.fore_color.rgb = white if row_index % 2 else RGBColor(248, 250, 252)
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    paragraph.font.name = "Microsoft YaHei"
                    paragraph.font.size = Pt(16)
                    paragraph.font.color.rgb = white if row_index == 0 else ink
                    paragraph.alignment = PP_ALIGN.CENTER

    def add_notes(slide, presenter_notes: str, refs: list[str], blocks) -> None:
        notes = slide.notes_slide.notes_text_frame
        notes.clear()
        content = presenter_notes.strip()
        teacher_answers = [block.teacher_answer for block in blocks if block.teacher_answer]
        if teacher_answers:
            content = f"{content}\n\n" if content else ""
            content += "[Teacher answers]\n" + "\n".join(f"- {answer}" for answer in teacher_answers)
        if refs:
            source_block = "\n".join(f"- {ref}" for ref in refs)
            content = f"{content}\n\n" if content else ""
            content += f"[Sources]\n{source_block}"
        notes.text = content

    def add_title(slide, title: str, eyebrow: str):
        add_text(slide, eyebrow.upper(), 0.65, 0.45, 5.3, 0.22, 10, blue, bold=True)
        add_text(slide, title, 0.65, 0.76, 11.8, 0.65, 35, navy, bold=True)
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
            add_text(slide, item.title, 1.25, 2.1, 9.8, 1.25, 50, white, bold=True)
            subtitle = " · ".join(item.bullets[:2]) or class_name
            add_text(slide, subtitle, 1.25, 3.72, 8.7, 0.4, 19, RGBColor(226, 232, 240))
            add_text(slide, "智教慧学 · AI 教案", 1.25, 5.72, 4.0, 0.28, 12, RGBColor(191, 219, 254))
        else:
            add_title(slide, item.title, item.layout.replace("_", " "))
            if item.layout == "knowledge_map":
                diagram_y = add_takeaway(slide, item.takeaway)
                # Draw connectors before the nodes so the hierarchy stays visible
                # without preventing teachers from editing any individual node.
                side_y = diagram_y + 0.05
                center_y = diagram_y + 0.30
                bottom_y = diagram_y + 2.05
                for x, y, w, h in (
                    (3.55, side_y + 0.39, 0.96, 0.07),
                    (8.52, side_y + 0.39, 0.96, 0.07),
                    (6.47, center_y + 1.10, 0.07, bottom_y - center_y - 1.10),
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
                center = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.45), Inches(center_y), Inches(4.1), Inches(1.1))
                center.fill.solid()
                center.fill.fore_color.rgb = blue
                center.line.fill.background()
                center_text = item.diagram_center or (item.bullets[0] if item.bullets else item.title)
                center_size = 18 if len(center_text) > 18 else 20
                add_text(slide, center_text[:36], 4.72, center_y + 0.38, 3.56, 0.52, center_size, white, bold=True, align=PP_ALIGN.CENTER)
                supplied_labels = item.diagram_nodes or item.bullets[1:4]
                labels = [
                    str(supplied_labels[0])[:22] if len(supplied_labels) > 0 else "前置知识",
                    str(supplied_labels[1])[:22] if len(supplied_labels) > 1 else "后续应用",
                    str(supplied_labels[2])[:22] if len(supplied_labels) > 2 else "学习迁移",
                ]
                positions = [(0.95, side_y), (9.45, side_y), (5.2, bottom_y)]
                for label, (x, y) in zip(labels, positions):
                    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(2.65), Inches(0.86))
                    box.fill.solid()
                    box.fill.fore_color.rgb = white
                    box.line.color.rgb = border
                    label_size = 13 if len(label) > 14 else 15
                    add_text(slide, label, x + 0.18, y + 0.19, 2.29, 0.48, label_size, ink, bold=True, align=PP_ALIGN.CENTER)
            elif item.layout in {"example", "activity"}:
                add_process(slide, item, add_takeaway(slide, item.takeaway))
            elif item.layout == "concept":
                start_y = add_takeaway(slide, item.takeaway)
                code_block = _block_of_type(item, "code")
                table_block = _block_of_type(item, "table")
                if code_block is not None:
                    add_code(slide, code_block, start_y)
                elif table_block is not None:
                    add_table(slide, table_block, start_y)
                else:
                    add_concept(slide, item, start_y)
            elif item.layout == "comparison":
                start_y = add_takeaway(slide, item.takeaway)
                table_block = _block_of_type(item, "table")
                add_table(slide, table_block, start_y) if table_block is not None else add_comparison(slide, item, start_y)
            elif item.layout == "review":
                add_question(slide, item, add_takeaway(slide, item.takeaway))
            elif item.layout in {"objectives", "review", "summary"}:
                add_cards(slide, _card_texts(item), add_takeaway(slide, item.takeaway), blue)
            elif item.layout == "difficulty_focus":
                add_cards(slide, _card_texts(item), add_takeaway(slide, item.takeaway), RGBColor(217, 119, 6))
            else:
                add_bullets(slide, item, add_takeaway(slide, item.takeaway))
        add_notes(slide, item.presenter_notes, item.source_refs, item.blocks)
        add_footer(slide, index, item.source_refs)

    prs.save(output_path)
    return output_path, filename
