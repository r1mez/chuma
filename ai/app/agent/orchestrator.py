"""Agent 主循环 — 多步推理 + 工具调用"""
import asyncio
import json
import logging
from collections.abc import AsyncIterator

from app.agent.tool_registry import ToolRegistry
from app.engines.llm.client import LLMClient

logger = logging.getLogger(__name__)

FORCE_ANSWER_PROMPT = "请基于已有信息直接回答用户问题，不要再调用工具。如果信息不足，请如实说明。"

MAX_TURNS = 10
TOOL_TIMEOUT = 10.0


class AgentOrchestrator:
    """Agent 编排器 — 核心能力：多步推理 + 工具调用

    Usage:
        llm = LLMClient(default_profile=quick_profile())
        agent = AgentOrchestrator(user_id=1, llm_client=llm)
        async for chunk in agent.run("帮我复习红黑树", history=[]):
            # SSE event dicts: {"type": "tool_used"|"tool_result"|"content"|"done"}
    """

    def __init__(self, user_id: int, llm_client: LLMClient):
        self.user_id = user_id
        self.llm = llm_client

    @staticmethod
    def _build_system_prompt() -> str:
        """根据当前注册的工具动态生成系统提示词"""
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

    async def run(
        self,
        message: str,
        history: list[dict],
    ) -> AsyncIterator[dict]:
        """执行 Agent 循环，流式输出 SSE 事件

        Yields:
            {"type": "tool_used", "tool": str, "query": str}
            {"type": "tool_result", "tool": str, "preview": str}
            {"type": "content", "content": str}
            {"type": "done"}
            {"type": "error", "content": str}
        """
        # Build initial messages — prompt is dynamic so it captures MCP tools too
        messages: list[dict] = [
            {"role": "system", "content": self._build_system_prompt()},
        ]
        for h in history:
            # Only keep role + content to avoid serialization issues
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

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

                        # Append tool result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })

                    # Continue loop for next LLM call
                    continue

                # No tool calls — this is the final answer
                # Stream it to the user
                async for chunk in self.llm.stream(messages, temperature=0.7):
                    if chunk.get("content"):
                        yield {"type": "content", "content": chunk["content"]}

                yield {"type": "done"}
                return

            # Max turns reached without convergence — force final answer
            logger.warning(f"Agent reached max turns ({MAX_TURNS}), forcing final answer")
            messages.append({"role": "system", "content": FORCE_ANSWER_PROMPT})

            async for chunk in self.llm.stream(messages, temperature=0.7):
                if chunk.get("content"):
                    yield {"type": "content", "content": chunk["content"]}

            yield {"type": "done"}

        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            yield {"type": "error", "content": f"Agent 处理异常: {str(e)}"}
            yield {"type": "done"}
