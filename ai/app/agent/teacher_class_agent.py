"""Conversational Agent for teacher class analysis."""

from __future__ import annotations

from app.agent.context import AgentContext, current_agent_context
from app.agent.orchestrator import AgentOrchestrator
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.teacher_class_tools import CLASS_TOOL_NAMES
from app.engines.llm.client import LLMClient


TEACHER_CLASS_AGENT_TOOLS = CLASS_TOOL_NAMES | frozenset({"search_kg", "read_document"})


class TeacherClassAgent(AgentOrchestrator):
    """Read-only, scope-bound assistant for a teacher's selected class/course."""

    def __init__(self, context: AgentContext, llm_client: LLMClient):
        super().__init__(
            user_id=context.user_id,
            llm_client=llm_client,
            context=context,
            allowed_tools=TEACHER_CLASS_AGENT_TOOLS,
        )

    def _build_system_prompt(self) -> str:
        context = current_agent_context.get()
        if context is None:
            raise RuntimeError("Teacher class Agent requires an AgentContext")

        tools = ToolRegistry.get_definitions(TEACHER_CLASS_AGENT_TOOLS)
        tool_lines = [
            f"- {item['function']['name']}: {item['function']['description']}"
            for item in tools
        ]
        scope = (
            f"教师ID={context.teacher_id or context.user_id}, "
            f"班级ID={context.class_id}, 课程ID={context.course_id}"
        )
        graph_scope = ", ".join(context.graph_names) or "当前课程知识图谱"

        return f"""你是“智教慧学”的教师班级学情分析助手。

你的任务是基于数据库和知识图谱中的真实数据，帮助教师分析当前班级的学习情况。
当前数据范围：{scope}；知识图谱范围：{graph_scope}。

必须遵守：
1. 回答班级或学生数据问题前，优先调用合适的班级工具；不得凭空编造人数、掌握度、错题数量或学生结论。
2. 只能分析当前教师有权限访问的班级和课程，不得尝试查询其他范围。
3. 学生画像只返回教学分析所需的信息，不泄露密码、邮箱等无关隐私。
4. 对没有数据或查询失败要明确说明，不要把缺失数据当成零或虚构趋势。
5. 回答尽量给出数据依据、问题定位和可执行教学建议。

可用工具：
{chr(10).join(tool_lines)}

请使用中文回答教师问题。"""

