"""Agent 主循环 — 多步推理 + 工具调用"""
import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator

from app.agent.suggestions import generate_suggested_questions
from app.agent.tool_registry import ToolRegistry
from app.engines.llm.client import LLMClient
from app.kg_pipeline.neighbors import get_node_neighbors

logger = logging.getLogger(__name__)

FORCE_ANSWER_PROMPT = "请基于已有信息直接回答用户问题，不要再调用工具。如果信息不足，请如实说明。"

MAX_TURNS = 10
TOOL_TIMEOUT = 10.0


def _parse_first_kg_node(tool_result_text: str, graph_names: list[str]) -> dict | None:
    """Parse nodes from search_kg output text and return the best one by type priority.

    Expected format: "- {name} [{type}] (id:{id}, graph:{graph_name}): {description}"
    Type priority: Algorithm > DataStructure > Concept > Principle > Protocol > Term > Technology > Model > Chapter > others
    This ensures we pick a real knowledge point (e.g. "冒泡排序 [Algorithm]") over a
    chapter heading (e.g. "8.3.1 冒泡排序 [Chapter]").
    Returns dict with id, name, type, graph_name or None if parsing fails.
    """
    # Type priority: lower number = higher priority
    TYPE_PRIORITY: dict[str, int] = {
        "Algorithm": 1, "DataStructure": 1,
        "Concept": 2, "Principle": 2,
        "Protocol": 3, "Technology": 3,
        "Term": 4, "Model": 4,
        "Chapter": 10,
    }
    DEFAULT_PRIORITY = 5

    # Parse ALL node lines from the text
    pattern = r'-\s+(.+?)\s+\[(\w+)\]\s+\(id:([^,\)]+),\s*graph:([^\)]+)\):\s+(.*)'
    candidates: list[dict] = []
    for match in re.finditer(pattern, tool_result_text):
        candidates.append({
            "id": match.group(3),
            "name": match.group(1),
            "type": match.group(2),
            "graph_name": match.group(4).strip() or (graph_names[0] if graph_names else ""),
        })

    if candidates:
        # Sort by type priority, then by name length (shorter = more specific)
        candidates.sort(key=lambda n: (TYPE_PRIORITY.get(n["type"], DEFAULT_PRIORITY), len(n["name"])))
        return candidates[0]

    # Fallback: accept the pre-graph format emitted by older AI processes.
    pattern_old = r'-\s+(.+?)\s+\[(\w+)\]\s+\(id:([^\)]+)\):\s+(.*)'
    match_old = re.search(pattern_old, tool_result_text)
    if match_old:
        return {
            "id": match_old.group(3),
            "name": match_old.group(1),
            "type": match_old.group(2),
            "graph_name": graph_names[0] if graph_names else "",
        }

    # Last-resort fallback for very old results without an id.
    pattern_very_old = r'-\s+(.+?)\s+\[(\w+)\]:\s+(.*)'
    match_very_old = re.search(pattern_very_old, tool_result_text)
    if match_very_old:
        return {
            "id": "",
            "name": match_very_old.group(1),
            "type": match_very_old.group(2),
            "graph_name": graph_names[0] if graph_names else "",
        }

    return None


class AgentOrchestrator:
    """Agent 编排器 — 核心能力：多步推理 + 工具调用

    Usage:
        llm = LLMClient(default_profile=quick_profile())
        agent = AgentOrchestrator(user_id=1, llm_client=llm)
        async for chunk in agent.run("帮我复习红黑树", history=[]):
            # SSE event dicts: {"type": "tool_used"|"tool_result"|"kg_hit"|"content"|"done"}
    """

    def __init__(self, user_id: int, llm_client: LLMClient):
        self.user_id = user_id
        self.llm = llm_client
        self._kg_hit_info: dict | None = None  # Tracks last kg_hit for suggestions

    @staticmethod
    def _build_system_prompt() -> str:
        """根据当前注册的工具和教材上下文动态生成系统提示词"""
        from app.agent.context import current_kg_graph_ids, current_graph_names

        tools = ToolRegistry.get_definitions()

        local_tools = []
        db_tools = []
        web_tools = []
        kg_tools = []

        for t in tools:
            name = t["function"]["name"]
            desc = t["function"]["description"]
            if any(kw in name for kw in ("postgresql", "postgres", "sql", "table", "schema")):
                db_tools.append((name, desc))
            elif any(kw in desc for kw in ("数据库", "表结构", "成绩", "SQL")):
                db_tools.append((name, desc))
            elif name == "search_kg":
                kg_tools.append((name, desc))
            elif name == "read_document":
                kg_tools.append((name, desc))
            elif "search" in name or "fetch" in name:
                web_tools.append((name, desc))
            else:
                local_tools.append((name, desc))

        lines = ["你是智教慧学，一个计算机科学学习智能助教，擅长408考研和数据库原理相关知识。"]
        lines.append("")

        # 注入教材上下文
        kg_ids = current_kg_graph_ids.get()
        g_names = current_graph_names.get()
        if kg_ids and g_names:
            lines.append("## 当前教材范围")
            lines.append("以下教材已被用户选中，请优先基于这些教材的知识图谱和文档内容回答：")
            for gid, gname in zip(kg_ids, g_names):
                # 从 graph_name 提取可读名称（去除 kg_xxx_ 前缀）
                readable = gname
                match = re.match(r'kg_(.+)_[a-f0-9]{8}$', gname)
                if match:
                    readable = match.group(1).replace('_', ' ')
                lines.append(f"- {readable} (id={gid})")
            lines.append("")

        lines.append("## 可用工具")

        if kg_tools:
            lines.append("")
            lines.append("### 📚 知识图谱 & 文档检索")
            for name, desc in kg_tools:
                lines.append(f"- `{name}`: {desc}")

        if db_tools:
            lines.append("")
            lines.append("### 🗄️ 数据库查询 (MCP)")
            for name, desc in db_tools:
                lines.append(f"- `{name}`: {desc}")
            lines.append("")
            lines.append("数据库查询步骤：")
            lines.append("1. 先调用 `list_tables` 了解表结构")
            lines.append("2. 调用 `describe_table` 确认字段")
            lines.append("3. 调用 `query_postgresql` 执行 SQL")

        if web_tools:
            lines.append("")
            lines.append("### 🌐 联网搜索")
            for name, desc in web_tools:
                lines.append(f"- `{name}`: {desc}")

        if local_tools:
            lines.append("")
            lines.append("### 🔧 其他工具")
            for name, desc in local_tools:
                lines.append(f"- `{name}`: {desc}")

        lines.append("")
        lines.append("## 回答要求")
        lines.append("- 使用中文回答")
        lines.append("- 基于工具返回的信息整合后给出清晰、有条理的回答")
        lines.append("- 如果工具查询无结果，如实告知并建议替代方案")
        lines.append("- 少用工具，一次能回答清楚的不要反复查")

        return "\n".join(lines)

    async def _emit_suggestions(self) -> dict | None:
        """Generate suggested questions based on the last kg_hit node.

        Returns an SSE event dict or None if suggestions cannot be generated.
        Silently fails on any error — suggestions are nice-to-have.
        """
        if not self._kg_hit_info:
            logger.info("No kg_hit_info, skipping suggestions")
            return None

        try:
            logger.info(f"Generating suggestions for node: {self._kg_hit_info}")
            neighbors = get_node_neighbors(
                node_id=self._kg_hit_info["id"],
                graph_name=self._kg_hit_info["graph_name"],
            )
            if not neighbors:
                logger.info("No neighbors found, skipping suggestions")
                return None

            # Build conversation context from last few messages
            context_parts = []
            for msg in self._messages[-4:]:  # Last 2 exchanges
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    context_parts.append(f"{role}: {content[:200]}")
            conversation_context = "\n".join(context_parts)

            questions = await generate_suggested_questions(
                hit_node_name=self._kg_hit_info["name"],
                hit_node_type=self._kg_hit_info["type"],
                neighbors=neighbors,
                conversation_context=conversation_context,
                llm_client=self.llm,
            )
            if not questions:
                logger.info("LLM returned no questions, skipping suggestions")
                return None

            logger.info(f"Generated {len(questions)} suggested questions")
            from dataclasses import asdict
            return {
                "type": "suggested_questions",
                "questions": [asdict(q) for q in questions],
            }
        except Exception as e:
            logger.warning(f"Failed to generate suggestions (non-critical): {e}", exc_info=True)
            return None

    async def run(
        self,
        message: str,
        history: list[dict],
        kg_graph_ids: list[int] | None = None,
        graph_names: list[str] | None = None,
    ) -> AsyncIterator[dict]:
        """执行 Agent 循环，流式输出 SSE 事件

        Yields:
            {"type": "tool_used", "tool": str, "query": str}
            {"type": "tool_result", "tool": str, "preview": str}
            {"type": "kg_hit", "node_id": str, "node_name": str, "node_type": str, "graph_name": str}
            {"type": "content", "content": str}
            {"type": "done"}
            {"type": "error", "content": str}
        """
        # Set contextvars for downstream use (system prompt reads these)
        from app.agent.context import current_kg_graph_ids, current_graph_names
        current_kg_graph_ids.set(kg_graph_ids or [])
        current_graph_names.set(graph_names or [])

        # Build initial messages — prompt is dynamic so it captures MCP tools too
        messages: list[dict] = [
            {"role": "system", "content": self._build_system_prompt()},
        ]
        for h in history:
            # Only keep role + content to avoid serialization issues
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})
        self._messages = messages  # Store for suggestions context

        tools = ToolRegistry.get_definitions()

        try:
            # Agent loop
            for turn in range(MAX_TURNS):
                response = await self.llm.chat(
                    messages,
                    tools=tools,
                    temperature=0.7,
                )

                # Process tool calls (priority over content, per spec)
                if response.tool_calls:

                    # First append assistant message with tool_calls
                    assistant_msg: dict = {
                        "role": "assistant",
                        "content": response.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                                },
                            }
                            for tc in response.tool_calls
                        ],
                    }
                    messages.append(assistant_msg)

                    # Execute each tool call
                    for tc in response.tool_calls:
                        # Notify frontend
                        yield {
                            "type": "tool_used",
                            "tool": tc.name,
                            "query": str(tc.arguments.get("query", tc.arguments)),
                        }

                        # Execute with timeout
                        try:
                            result = await asyncio.wait_for(
                                ToolRegistry.execute(tc.name, tc.arguments, self.user_id),
                                timeout=TOOL_TIMEOUT,
                            )
                        except asyncio.TimeoutError:
                            result = "工具调用超时"
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            result = f"执行出错: {str(e)}"

                        # Result preview (first 80 chars)
                        preview = result[:80] + "..." if len(result) > 80 else result
                        yield {
                            "type": "tool_result",
                            "tool": tc.name,
                            "preview": preview.replace("\n", " "),
                        }

                        # Emit kg_hit event when search_kg returns results
                        if tc.name == "search_kg" and not result.startswith("未在知识图谱中找到"):
                            g_names = current_graph_names.get()
                            hit_node = _parse_first_kg_node(result, g_names)
                            if hit_node:
                                self._kg_hit_info = hit_node  # Store for suggestions
                                yield {
                                    "type": "kg_hit",
                                    "node_id": hit_node["id"],
                                    "node_name": hit_node["name"],
                                    "node_type": hit_node["type"],
                                    "graph_name": hit_node["graph_name"],
                                }

                        # Append tool result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })

                    # Continue loop for next LLM call
                    continue

                # No tool calls — this is the final answer
                # Stream it to the user (pass tools with tool_choice=none to prevent
                # DeepSeek from emitting DSML tool-call markers in the content stream)
                async for chunk in self.llm.stream(messages, temperature=0.7, tools=tools, tool_choice="none"):
                    if chunk.get("content"):
                        yield {"type": "content", "content": chunk["content"]}

                # Emit suggested questions if a kg_hit occurred
                suggestions_event = await self._emit_suggestions()
                if suggestions_event:
                    yield suggestions_event

                yield {"type": "done"}
                return

            # Max turns reached without convergence — force final answer
            logger.warning(f"Agent reached max turns ({MAX_TURNS}), forcing final answer")
            messages.append({"role": "system", "content": FORCE_ANSWER_PROMPT})

            async for chunk in self.llm.stream(messages, temperature=0.7, tools=tools, tool_choice="none"):
                if chunk.get("content"):
                    yield {"type": "content", "content": chunk["content"]}

            # Emit suggested questions if a kg_hit occurred
            suggestions_event = await self._emit_suggestions()
            if suggestions_event:
                yield suggestions_event

            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            yield {"type": "error", "content": f"Agent 处理异常: {str(e)}"}
            yield {"type": "done"}
